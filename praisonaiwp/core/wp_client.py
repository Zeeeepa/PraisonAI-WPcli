"""WordPress CLI client for PraisonAIWP"""

import json
from typing import Any, Dict, List, Optional

from praisonaiwp.core.ssh_manager import SSHManager
from praisonaiwp.utils.exceptions import WPCLIError
from praisonaiwp.utils.logger import get_logger

logger = get_logger(__name__)


class WPClient:
    """WordPress CLI operations wrapper"""

    def __init__(
        self,
        ssh: SSHManager,
        wp_path: str,
        php_bin: str = 'php',
        wp_cli: str = '/usr/local/bin/wp',
        verify_installation: bool = True
    ):
        """
        Initialize WP Client

        Args:
            ssh: SSH Manager instance
            wp_path: WordPress installation path
            php_bin: PHP binary path (default: 'php')
            wp_cli: WP-CLI binary path (default: '/usr/local/bin/wp')
            verify_installation: Verify WP-CLI and WordPress are available (default: True)
        """
        self.ssh = ssh
        self.wp_path = wp_path
        self.php_bin = php_bin
        self.wp_cli = wp_cli

        logger.debug(f"Initialized WPClient for {wp_path}")

        # Verify installation if requested
        if verify_installation:
            self._verify_installation()

    def _verify_installation(self):
        """
        Verify WP-CLI and WordPress installation

        Raises:
            WPCLIError: If WP-CLI or WordPress not found
        """
        try:
            # Check if WP-CLI binary exists
            stdout, stderr = self.ssh.execute(f"test -f {self.wp_cli} && echo 'exists' || echo 'not found'")

            if 'not found' in stdout:
                raise WPCLIError(
                    f"WP-CLI not found at {self.wp_cli}\n"
                    f"\nInstallation instructions:\n"
                    f"1. Download: curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar\n"
                    f"2. Make executable: chmod +x wp-cli.phar\n"
                    f"3. Move to path: sudo mv wp-cli.phar {self.wp_cli}\n"
                    f"\nOr specify correct path with --wp-cli option"
                )

            # Check if WordPress directory exists
            stdout, stderr = self.ssh.execute(f"test -d {self.wp_path} && echo 'exists' || echo 'not found'")

            if 'not found' in stdout:
                raise WPCLIError(
                    f"WordPress installation not found at {self.wp_path}\n"
                    f"Please verify the WordPress path is correct."
                )

            # Check if wp-config.php exists
            stdout, stderr = self.ssh.execute(f"test -f {self.wp_path}/wp-config.php && echo 'exists' || echo 'not found'")

            if 'not found' in stdout:
                raise WPCLIError(
                    f"wp-config.php not found in {self.wp_path}\n"
                    f"This doesn't appear to be a valid WordPress installation."
                )

            # Test WP-CLI execution
            stdout, stderr = self.ssh.execute(f"cd {self.wp_path} && {self.php_bin} {self.wp_cli} --version")

            if stderr and ('command not found' in stderr.lower() or 'no such file' in stderr.lower()):
                raise WPCLIError(
                    f"Failed to execute WP-CLI\n"
                    f"Error: {stderr}\n"
                    f"\nPossible issues:\n"
                    f"1. PHP binary not found: {self.php_bin}\n"
                    f"2. WP-CLI not executable: {self.wp_cli}\n"
                    f"3. Missing PHP extensions (mysql, mysqli)\n"
                    f"\nFor Plesk servers, try: /opt/plesk/php/8.3/bin/php"
                )

            if 'WP-CLI' in stdout:
                logger.info(f"WP-CLI verified: {stdout.strip()}")
            else:
                logger.warning(f"WP-CLI verification returned unexpected output: {stdout}")

        except WPCLIError:
            raise
        except Exception as e:
            logger.warning(f"Could not verify WP-CLI installation: {e}")

    def wp(self, *args, **kwargs) -> Any:
        """
        Generic WP-CLI command executor - supports ANY WP-CLI command

        This method provides direct access to WP-CLI without needing specific wrapper methods.
        Arguments are automatically converted to WP-CLI flags and options.

        Args:
            *args: Command parts (e.g., 'post', 'list')
            **kwargs: Command options (converted to --key=value flags)
                     - Use True for boolean flags (e.g., porcelain=True -> --porcelain)
                     - Use format='json' for automatic JSON parsing
                     - Underscores in keys are converted to hyphens (dry_run -> --dry-run)

        Returns:
            Command output (string), or parsed JSON if format='json'

        Examples:
            # Create a user
            wp('user', 'create', 'john', 'john@example.com', role='editor', porcelain=True)

            # List posts
            posts = wp('post', 'list', status='publish', format='json')

            # Flush cache
            wp('cache', 'flush')

            # Search and replace
            wp('search-replace', 'old', 'new', dry_run=True)

            # Plugin operations
            wp('plugin', 'activate', 'akismet')
            wp('plugin', 'list', status='active', format='json')

        Raises:
            WPCLIError: If command fails
        """
        # Build command from args
        cmd_parts = list(args)

        # Add kwargs as flags/options
        auto_parse_json = False
        for key, value in kwargs.items():
            # Convert underscores to hyphens for WP-CLI convention
            flag_key = key.replace('_', '-')

            if value is True:
                # Boolean flag (e.g., --porcelain, --dry-run)
                cmd_parts.append(f"--{flag_key}")
            elif value is not False and value is not None:
                # Key-value option
                if flag_key == 'format' and value == 'json':
                    auto_parse_json = True

                # Escape single quotes in values
                escaped_value = str(value).replace("'", "'\\''")
                cmd_parts.append(f"--{flag_key}='{escaped_value}'")

        # Execute command
        cmd = ' '.join(cmd_parts)
        result = self._execute_wp(cmd)

        # Auto-parse JSON if format=json
        if auto_parse_json and result.strip():
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON output: {result[:100]}")
                return result

        return result.strip() if result else ""

    def _execute_wp(self, command: str) -> str:
        """
        Execute WP-CLI command (internal method)

        Args:
            command: WP-CLI command (without 'wp' prefix)

        Returns:
            Command output

        Raises:
            WPCLIError: If command fails
        """
        full_cmd = f"cd {self.wp_path} && {self.php_bin} {self.wp_cli} {command}"

        logger.debug(f"Executing WP-CLI: {command}")

        try:
            stdout, stderr = self.ssh.execute(full_cmd)
        except Exception as e:
            raise WPCLIError(f"Failed to execute WP-CLI command: {e}")

        # Check for common error patterns
        if stderr:
            error_lower = stderr.lower()

            if 'command not found' in error_lower:
                raise WPCLIError(
                    f"WP-CLI command not found\n"
                    f"Error: {stderr}\n"
                    f"\nPlease verify:\n"
                    f"1. WP-CLI is installed at: {self.wp_cli}\n"
                    f"2. PHP binary is correct: {self.php_bin}"
                )

            if 'no such file or directory' in error_lower:
                raise WPCLIError(
                    f"File or directory not found\n"
                    f"Error: {stderr}\n"
                    f"\nPlease verify:\n"
                    f"1. WordPress path: {self.wp_path}\n"
                    f"2. WP-CLI path: {self.wp_cli}"
                )

            if 'error:' in error_lower:
                # Don't log "Term doesn't exist" as error - it's expected when looking up categories by name
                if "term doesn't exist" not in error_lower:
                    logger.error(f"WP-CLI error: {stderr}")
                raise WPCLIError(f"WP-CLI error: {stderr}")

        return stdout.strip()

    def get_post(self, post_id: int, field: Optional[str] = None) -> Any:
        """
        Get post data

        Args:
            post_id: Post ID
            field: Specific field to retrieve (optional)

        Returns:
            Post data (dict if no field specified, str if field specified)
        """
        cmd = f"post get {post_id}"

        if field:
            cmd += f" --field={field}"
            result = self._execute_wp(cmd)
            return result
        else:
            cmd += " --format=json"
            result = self._execute_wp(cmd)
            return json.loads(result)

    def get_default_user(self) -> Optional[str]:
        """
        Get the default admin user (user with ID 1 or first admin user)

        Returns:
            User login name or None if not found
        """
        try:
            # Try to get user with ID 1 (typically the first admin)
            cmd = "user get 1 --field=user_login"
            result = self._execute_wp(cmd)
            return result.strip()
        except Exception:
            try:
                # Fallback: get first admin user
                cmd = "user list --role=administrator --field=user_login --format=csv"
                result = self._execute_wp(cmd)
                users = result.strip().split('\n')
                if users and users[0]:
                    return users[0]
            except Exception as e:
                logger.warning(f"Could not get default user: {e}")
        return None

    def create_post(self, **kwargs) -> int:
        """
        Create a new post

        Args:
            **kwargs: Post fields (post_title, post_content, post_status, etc.)

        Returns:
            Created post ID
        """
        # Auto-set author to default admin if not specified
        if 'post_author' not in kwargs:
            default_user = self.get_default_user()
            if default_user:
                kwargs['post_author'] = default_user
                logger.debug(f"Using default author: {default_user}")

        args = []
        for key, value in kwargs.items():
            # Escape single quotes in value
            escaped_value = str(value).replace("'", "'\\''")
            args.append(f"--{key}='{escaped_value}'")

        cmd = f"post create {' '.join(args)} --porcelain"
        result = self._execute_wp(cmd)

        post_id = int(result.strip())
        logger.info(f"Created post ID: {post_id}")

        return post_id

    def update_post(self, post_id: int, **kwargs) -> bool:
        """
        Update an existing post

        Args:
            post_id: Post ID to update
            **kwargs: Fields to update

        Returns:
            True if successful
        """
        args = []
        for key, value in kwargs.items():
            # Escape single quotes in value
            escaped_value = str(value).replace("'", "'\\''")
            args.append(f"--{key}='{escaped_value}'")

        cmd = f"post update {post_id} {' '.join(args)}"
        self._execute_wp(cmd)

        logger.info(f"Updated post ID: {post_id}")
        return True

    def delete_post(self, post_id: int, force: bool = False) -> bool:
        """
        Delete a post

        Args:
            post_id: Post ID to delete
            force: Skip trash and force deletion

        Returns:
            True if successful
        """
        force_flag = '--force' if force else ''
        cmd = f"post delete {post_id} {force_flag}"
        self._execute_wp(cmd)

        logger.info(f"Deleted post ID: {post_id}")
        return True

    def post_exists(self, post_id: int) -> bool:
        """
        Check if a post exists

        Args:
            post_id: Post ID to check

        Returns:
            True if post exists, False otherwise
        """
        try:
            cmd = f"post exists {post_id}"
            self._execute_wp(cmd)
            logger.debug(f"Post {post_id} exists")
            return True
        except WPCLIError:
            logger.debug(f"Post {post_id} does not exist")
            return False

    def get_post_meta(self, post_id: int, key: str = None) -> Any:
        """
        Get post meta value(s)

        Args:
            post_id: Post ID
            key: Meta key (if None, returns all meta)

        Returns:
            Meta value or dict of all meta
        """
        if key:
            cmd = f"post meta get {post_id} {key}"
            result = self._execute_wp(cmd)
            return result.strip()
        else:
            cmd = f"post meta list {post_id} --format=json"
            result = self._execute_wp(cmd)
            return json.loads(result)

    def set_post_meta(self, post_id: int, key: str, value: str) -> bool:
        """
        Set post meta value

        Args:
            post_id: Post ID
            key: Meta key
            value: Meta value

        Returns:
            True if successful
        """
        escaped_value = str(value).replace("'", "'\\''")
        cmd = f"post meta set {post_id} {key} '{escaped_value}'"
        self._execute_wp(cmd)
        logger.info(f"Set meta {key} for post {post_id}")
        return True

    def delete_post_meta(self, post_id: int, key: str) -> bool:
        """
        Delete post meta

        Args:
            post_id: Post ID
            key: Meta key

        Returns:
            True if successful
        """
        cmd = f"post meta delete {post_id} {key}"
        self._execute_wp(cmd)
        logger.info(f"Deleted meta {key} from post {post_id}")
        return True

    def update_post_meta(self, post_id: int, key: str, value: str) -> bool:
        """
        Update post meta value

        Args:
            post_id: Post ID
            key: Meta key
            value: Meta value

        Returns:
            True if successful
        """
        escaped_value = str(value).replace("'", "'\\''")
        cmd = f"post meta update {post_id} {key} '{escaped_value}'"
        self._execute_wp(cmd)
        logger.info(f"Updated meta {key} for post {post_id}")
        return True

    def list_users(self, **filters) -> List[Dict[str, Any]]:
        """
        List users with filters

        Args:
            **filters: Filters (role, search, etc.)

        Returns:
            List of user dictionaries
        """
        args = ["--format=json"]

        for key, value in filters.items():
            args.append(f"--{key}={value}")

        cmd = f"user list {' '.join(args)}"
        result = self._execute_wp(cmd)

        return json.loads(result)

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Get user details

        Args:
            user_id: User ID

        Returns:
            User dictionary
        """
        cmd = f"user get {user_id} --format=json"
        result = self._execute_wp(cmd)

        return json.loads(result)

    def create_user(self, username: str, email: str, **kwargs) -> int:
        """
        Create a new user

        Args:
            username: Username
            email: Email address
            **kwargs: Additional user fields (role, user_pass, display_name, etc.)

        Returns:
            User ID
        """
        args = [username, email]

        for key, value in kwargs.items():
            escaped_value = str(value).replace("'", "'\\''")
            args.append(f"--{key}='{escaped_value}'")

        cmd = f"user create {' '.join(args)} --porcelain"
        result = self._execute_wp(cmd)
        user_id = int(result.strip())
        logger.info(f"Created user {username} with ID {user_id}")
        return user_id

    def update_user(self, user_id: int, **kwargs) -> bool:
        """
        Update user fields

        Args:
            user_id: User ID
            **kwargs: User fields to update

        Returns:
            True if successful
        """
        args = [str(user_id)]

        for key, value in kwargs.items():
            escaped_value = str(value).replace("'", "'\\''")
            args.append(f"--{key}='{escaped_value}'")

        cmd = f"user update {' '.join(args)}"
        self._execute_wp(cmd)
        logger.info(f"Updated user {user_id}")
        return True

    def delete_user(self, user_id: int, reassign: int = None) -> bool:
        """
        Delete a user

        Args:
            user_id: User ID to delete
            reassign: User ID to reassign posts to (optional)

        Returns:
            True if successful
        """
        args = [str(user_id), "--yes"]

        if reassign is not None:
            args.append(f"--reassign={reassign}")

        cmd = f"user delete {' '.join(args)}"
        self._execute_wp(cmd)
        logger.info(f"Deleted user {user_id}")
        return True

    def get_option(self, option_name: str) -> str:
        """
        Get WordPress option value

        Args:
            option_name: Option name

        Returns:
            Option value
        """
        cmd = f"option get {option_name}"
        result = self._execute_wp(cmd)

        return result.strip()

    def set_option(self, option_name: str, value: str) -> bool:
        """
        Set WordPress option value

        Args:
            option_name: Option name
            value: Option value

        Returns:
            True if successful
        """
        escaped_value = str(value).replace("'", "'\\''")
        cmd = f"option set {option_name} '{escaped_value}'"
        self._execute_wp(cmd)
        logger.info(f"Set option {option_name}")
        return True

    def delete_option(self, option_name: str) -> bool:
        """
        Delete WordPress option

        Args:
            option_name: Option name

        Returns:
            True if successful
        """
        cmd = f"option delete {option_name}"
        self._execute_wp(cmd)
        logger.info(f"Deleted option {option_name}")
        return True

    def list_plugins(self, **filters) -> List[Dict[str, Any]]:
        """
        List installed plugins

        Args:
            **filters: Filters (status, etc.)

        Returns:
            List of plugin dictionaries
        """
        args = ["--format=json"]

        for key, value in filters.items():
            args.append(f"--{key}={value}")

        cmd = f"plugin list {' '.join(args)}"
        result = self._execute_wp(cmd)

        return json.loads(result)

    def list_themes(self, **filters) -> List[Dict[str, Any]]:
        """
        List installed themes

        Args:
            **filters: Filters (status, etc.)

        Returns:
            List of theme dictionaries
        """
        args = ["--format=json"]

        for key, value in filters.items():
            args.append(f"--{key}={value}")

        cmd = f"theme list {' '.join(args)}"
        result = self._execute_wp(cmd)

        return json.loads(result)

    def activate_plugin(self, plugin: str) -> bool:
        """
        Activate a plugin

        Args:
            plugin: Plugin slug or path

        Returns:
            True if successful
        """
        cmd = f"plugin activate {plugin}"
        self._execute_wp(cmd)
        logger.info(f"Activated plugin {plugin}")
        return True

    def deactivate_plugin(self, plugin: str) -> bool:
        """
        Deactivate a plugin

        Args:
            plugin: Plugin slug or path

        Returns:
            True if successful
        """
        cmd = f"plugin deactivate {plugin}"
        self._execute_wp(cmd)
        logger.info(f"Deactivated plugin {plugin}")
        return True

    def update_plugin(self, plugin: str = "all") -> bool:
        """
        Update one or all plugins

        Args:
            plugin: Plugin slug/path or "all" to update all plugins

        Returns:
            True if successful
        """
        if plugin == "all":
            cmd = "plugin update --all"
        else:
            cmd = f"plugin update {plugin}"
        self._execute_wp(cmd)
        logger.info(f"Updated plugin(s): {plugin}")
        return True

    def activate_theme(self, theme: str) -> bool:
        """
        Activate a theme

        Args:
            theme: Theme slug

        Returns:
            True if successful
        """
        cmd = f"theme activate {theme}"
        self._execute_wp(cmd)
        logger.info(f"Activated theme {theme}")
        return True

    def get_user_meta(self, user_id: int, key: str = None) -> Any:
        """
        Get user meta value(s)

        Args:
            user_id: User ID
            key: Meta key (optional, returns all if not specified)

        Returns:
            Meta value or list of all meta
        """
        if key:
            cmd = f"user meta get {user_id} {key}"
            result = self._execute_wp(cmd)
            return result.strip()
        else:
            cmd = f"user meta list {user_id} --format=json"
            result = self._execute_wp(cmd)
            return json.loads(result)

    def set_user_meta(self, user_id: int, key: str, value: str) -> bool:
        """
        Set user meta value

        Args:
            user_id: User ID
            key: Meta key
            value: Meta value

        Returns:
            True if successful
        """
        escaped_value = str(value).replace("'", "'\\''")
        cmd = f"user meta add {user_id} {key} '{escaped_value}'"
        self._execute_wp(cmd)
        logger.info(f"Set meta {key} for user {user_id}")
        return True

    def update_user_meta(self, user_id: int, key: str, value: str) -> bool:
        """
        Update user meta value

        Args:
            user_id: User ID
            key: Meta key
            value: Meta value

        Returns:
            True if successful
        """
        escaped_value = str(value).replace("'", "'\\''")
        cmd = f"user meta update {user_id} {key} '{escaped_value}'"
        self._execute_wp(cmd)
        logger.info(f"Updated meta {key} for user {user_id}")
        return True

    def delete_user_meta(self, user_id: int, key: str) -> bool:
        """
        Delete user meta

        Args:
            user_id: User ID
            key: Meta key

        Returns:
            True if successful
        """
        cmd = f"user meta delete {user_id} {key}"
        self._execute_wp(cmd)
        logger.info(f"Deleted meta {key} for user {user_id}")
        return True

    def flush_cache(self) -> bool:
        """
        Flush object cache

        Returns:
            True if successful
        """
        cmd = "cache flush"
        self._execute_wp(cmd)
        logger.info("Flushed cache")
        return True

    def get_cache_type(self) -> str:
        """
        Get cache type

        Returns:
            Cache type string
        """
        cmd = "cache type"
        result = self._execute_wp(cmd)
        return result.strip()

    def get_transient(self, key: str) -> str:
        """
        Get transient value

        Args:
            key: Transient key

        Returns:
            Transient value
        """
        cmd = f"transient get {key}"
        result = self._execute_wp(cmd)
        return result.strip()

    def set_transient(self, key: str, value: str, expiration: int = None) -> bool:
        """
        Set transient value

        Args:
            key: Transient key
            value: Transient value
            expiration: Expiration time in seconds (optional)

        Returns:
            True if successful
        """
        escaped_value = str(value).replace("'", "'\\''")
        cmd = f"transient set {key} '{escaped_value}'"
        if expiration:
            cmd += f" {expiration}"
        self._execute_wp(cmd)
        logger.info(f"Set transient {key}")
        return True

    def delete_transient(self, key: str) -> bool:
        """
        Delete transient

        Args:
            key: Transient key

        Returns:
            True if successful
        """
        cmd = f"transient delete {key}"
        self._execute_wp(cmd)
        logger.info(f"Deleted transient {key}")
        return True

    def list_menus(self) -> List[Dict[str, Any]]:
        """
        List navigation menus

        Returns:
            List of menu dictionaries
        """
        cmd = "menu list --format=json"
        result = self._execute_wp(cmd)
        return json.loads(result)

    def create_menu(self, name: str) -> int:
        """
        Create navigation menu

        Args:
            name: Menu name

        Returns:
            Menu ID
        """
        cmd = f"menu create '{name}' --porcelain"
        result = self._execute_wp(cmd)
        menu_id = int(result.strip())
        logger.info(f"Created menu {name} with ID {menu_id}")
        return menu_id

    def delete_menu(self, menu_id: int) -> bool:
        """
        Delete navigation menu

        Args:
            menu_id: Menu ID

        Returns:
            True if successful
        """
        cmd = f"menu delete {menu_id}"
        self._execute_wp(cmd)
        logger.info(f"Deleted menu {menu_id}")
        return True

    def add_menu_item(self, menu_id: int, **kwargs) -> int:
        """
        Add item to menu

        Args:
            menu_id: Menu ID
            **kwargs: Item properties (title, url, object-id, type, etc.)

        Returns:
            Menu item ID
        """
        args = []
        for key, value in kwargs.items():
            if isinstance(value, str):
                escaped_value = value.replace("'", "'\\''")
                args.append(f"--{key}='{escaped_value}'")
            else:
                args.append(f"--{key}={value}")

        cmd = f"menu item add-custom {menu_id} {' '.join(args)} --porcelain"
        result = self._execute_wp(cmd)
        item_id = int(result.strip())
        logger.info(f"Added menu item {item_id} to menu {menu_id}")
        return item_id

    def create_term(self, taxonomy: str, name: str, **kwargs) -> int:
        """
        Create a new term

        Args:
            taxonomy: Taxonomy name (category, post_tag, etc.)
            name: Term name
            **kwargs: Additional options (slug, description, parent, etc.)

        Returns:
            Term ID
        """
        args = []
        for key, value in kwargs.items():
            if isinstance(value, str):
                escaped_value = value.replace("'", "'\\''")
                args.append(f"--{key}='{escaped_value}'")
            else:
                args.append(f"--{key}={value}")

        escaped_name = name.replace("'", "'\\''")
        cmd = f"term create {taxonomy} '{escaped_name}' {' '.join(args)} --porcelain"
        result = self._execute_wp(cmd)
        term_id = int(result.strip())
        logger.info(f"Created term {name} in {taxonomy} with ID {term_id}")
        return term_id

    def delete_term(self, taxonomy: str, term_id: int) -> bool:
        """
        Delete a term

        Args:
            taxonomy: Taxonomy name
            term_id: Term ID

        Returns:
            True if successful
        """
        cmd = f"term delete {taxonomy} {term_id}"
        self._execute_wp(cmd)
        logger.info(f"Deleted term {term_id} from {taxonomy}")
        return True

    def update_term(self, taxonomy: str, term_id: int, **kwargs) -> bool:
        """
        Update a term

        Args:
            taxonomy: Taxonomy name
            term_id: Term ID
            **kwargs: Fields to update (name, slug, description, parent, etc.)

        Returns:
            True if successful
        """
        args = []
        for key, value in kwargs.items():
            if isinstance(value, str):
                escaped_value = value.replace("'", "'\\''")
                args.append(f"--{key}='{escaped_value}'")
            else:
                args.append(f"--{key}={value}")

        cmd = f"term update {taxonomy} {term_id} {' '.join(args)}"
        self._execute_wp(cmd)
        logger.info(f"Updated term {term_id} in {taxonomy}")
        return True

    def get_core_version(self) -> str:
        """
        Get WordPress core version

        Returns:
            WordPress version string
        """
        cmd = "core version"
        result = self._execute_wp(cmd)
        return result.strip()

    def core_is_installed(self) -> bool:
        """
        Check if WordPress is installed

        Returns:
            True if WordPress is installed
        """
        try:
            cmd = "core is-installed"
            self._execute_wp(cmd)
            return True
        except Exception:
            return False

    def import_media(self, file_path: str, post_id: int = None, **kwargs) -> int:
        """
        Import media file to WordPress

        Args:
            file_path: Path to media file
            post_id: Post ID to attach to (optional)
            **kwargs: Additional options (title, caption, alt, desc, etc.)

        Returns:
            Attachment ID
        """
        args = [f"'{file_path}'"]

        if post_id is not None:
            args.append(f"--post_id={post_id}")

        for key, value in kwargs.items():
            escaped_value = str(value).replace("'", "'\\''")
            args.append(f"--{key}='{escaped_value}'")

        args.append("--porcelain")

        cmd = f"media import {' '.join(args)}"
        result = self._execute_wp(cmd)
        attachment_id = int(result.strip())
        logger.info(f"Imported media {file_path} with ID {attachment_id}")
        return attachment_id

    def get_media_info(self, attachment_id: int, field: Optional[str] = None) -> Any:
        """
        Get media/attachment information

        Args:
            attachment_id: Attachment ID
            field: Specific field to retrieve (guid, post_title, post_mime_type, etc.)

        Returns:
            Attachment data (dict if no field specified, str if field specified)
        """
        return self.get_post(attachment_id, field=field)

    def get_media_url(self, attachment_id: int) -> str:
        """
        Get media URL

        Args:
            attachment_id: Attachment ID

        Returns:
            Media URL
        """
        url = self.get_post(attachment_id, field='guid')
        logger.info(f"Retrieved URL for attachment {attachment_id}: {url}")
        return url.strip()

    def list_media(self, post_id: int = None, **filters) -> List[Dict[str, Any]]:
        """
        List media/attachments

        Args:
            post_id: Filter by parent post ID (optional)
            **filters: Additional filters (mime_type, etc.)

        Returns:
            List of attachment dictionaries
        """
        list_filters = {'post_type': 'attachment'}

        if post_id is not None:
            list_filters['post_parent'] = post_id

        list_filters.update(filters)

        return self.list_posts(**list_filters)

    def list_comments(self, **filters) -> List[Dict[str, Any]]:
        """
        List comments with filters

        Args:
            **filters: Filters (status, post_id, etc.)

        Returns:
            List of comment dictionaries
        """
        args = ["--format=json"]

        for key, value in filters.items():
            args.append(f"--{key}={value}")

        cmd = f"comment list {' '.join(args)}"
        result = self._execute_wp(cmd)

        return json.loads(result)

    def get_comment(self, comment_id: int) -> Dict[str, Any]:
        """
        Get comment details

        Args:
            comment_id: Comment ID

        Returns:
            Comment dictionary
        """
        cmd = f"comment get {comment_id} --format=json"
        result = self._execute_wp(cmd)

        return json.loads(result)

    def create_comment(self, post_id: int, **kwargs) -> int:
        """
        Create a new comment

        Args:
            post_id: Post ID
            **kwargs: Comment fields (comment_content, comment_author, etc.)

        Returns:
            Comment ID
        """
        args = [str(post_id)]

        for key, value in kwargs.items():
            escaped_value = str(value).replace("'", "'\\''")
            args.append(f"--{key}='{escaped_value}'")

        args.append("--porcelain")

        cmd = f"comment create {' '.join(args)}"
        result = self._execute_wp(cmd)
        comment_id = int(result.strip())
        logger.info(f"Created comment {comment_id} on post {post_id}")
        return comment_id

    def update_comment(self, comment_id: int, **kwargs) -> bool:
        """
        Update comment fields

        Args:
            comment_id: Comment ID
            **kwargs: Comment fields to update

        Returns:
            True if successful
        """
        args = [str(comment_id)]

        for key, value in kwargs.items():
            escaped_value = str(value).replace("'", "'\\''")
            args.append(f"--{key}='{escaped_value}'")

        cmd = f"comment update {' '.join(args)}"
        self._execute_wp(cmd)
        logger.info(f"Updated comment {comment_id}")
        return True

    def delete_comment(self, comment_id: int, force: bool = False) -> bool:
        """
        Delete a comment

        Args:
            comment_id: Comment ID
            force: Bypass trash and force deletion

        Returns:
            True if successful
        """
        args = [str(comment_id)]

        if force:
            args.append("--force")

        cmd = f"comment delete {' '.join(args)}"
        self._execute_wp(cmd)
        logger.info(f"Deleted comment {comment_id}")
        return True

    def approve_comment(self, comment_id: int) -> bool:
        """
        Approve a comment

        Args:
            comment_id: Comment ID

        Returns:
            True if successful
        """
        cmd = f"comment approve {comment_id}"
        self._execute_wp(cmd)
        logger.info(f"Approved comment {comment_id}")
        return True

    def list_posts(
        self,
        post_type: str = 'post',
        **filters
    ) -> List[Dict[str, Any]]:
        """
        List posts with filters

        Args:
            post_type: Post type (default: 'post')
            **filters: Additional filters (post_status, etc.)

        Returns:
            List of post dictionaries
        """
        args = [f"--post_type={post_type}", "--format=json"]

        for key, value in filters.items():
            args.append(f"--{key}={value}")

        cmd = f"post list {' '.join(args)}"
        result = self._execute_wp(cmd)

        return json.loads(result)

    def db_query(self, query: str) -> str:
        """
        Execute database query

        Args:
            query: SQL query

        Returns:
            Query result as JSON string
        """
        # Escape query for shell
        escaped_query = query.replace('"', '\\"').replace('$', '\\$')
        cmd = f'db query "{escaped_query}" --format=json'

        return self._execute_wp(cmd)

    def search_replace(
        self,
        old: str,
        new: str,
        tables: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> str:
        """
        Search and replace in database

        Args:
            old: Text to find
            new: Replacement text
            tables: Tables to search (optional)
            dry_run: Preview changes without applying

        Returns:
            Command output
        """
        cmd = f"search-replace '{old}' '{new}'"

        if tables:
            cmd += f" {' '.join(tables)}"

        if dry_run:
            cmd += " --dry-run"

        return self._execute_wp(cmd)

    def set_post_categories(self, post_id: int, category_ids: List[int]) -> bool:
        """
        Set post categories (replace all existing)

        Args:
            post_id: Post ID
            category_ids: List of category IDs

        Returns:
            True if successful
        """
        if not category_ids:
            logger.warning("No category IDs provided")
            return False

        # Join category IDs with comma
        cat_ids_str = ','.join(map(str, category_ids))
        cmd = f"post update {post_id} --post_category={cat_ids_str}"

        try:
            self._execute_wp(cmd)
            logger.info(f"Set categories {cat_ids_str} for post {post_id}")
        except WPCLIError as e:
            # WP-CLI sometimes reports "Term doesn't exist" but still sets the category
            # Verify if categories were actually set
            if "Term doesn't exist" in str(e):
                post_data = self.get_post(post_id)
                if post_data and 'post_category' in str(post_data):
                    logger.info(f"Categories {cat_ids_str} set successfully (ignoring WP-CLI warning)")
                    return True
            # Re-raise if it's a real error
            raise

        return True

    def add_post_category(self, post_id: int, category_id: int) -> bool:
        """
        Add a category to post (append)

        Args:
            post_id: Post ID
            category_id: Category ID to add

        Returns:
            True if successful
        """
        cmd = f"post term add {post_id} category {category_id}"

        self._execute_wp(cmd)
        logger.info(f"Added category {category_id} to post {post_id}")

        return True

    def remove_post_category(self, post_id: int, category_id: int) -> bool:
        """
        Remove a category from post

        Args:
            post_id: Post ID
            category_id: Category ID to remove

        Returns:
            True if successful
        """
        cmd = f"post term remove {post_id} category {category_id}"

        self._execute_wp(cmd)
        logger.info(f"Removed category {category_id} from post {post_id}")

        return True

    def list_categories(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all categories

        Args:
            search: Optional search query

        Returns:
            List of category dictionaries
        """
        cmd = "term list category --format=json --fields=term_id,name,slug,parent,count"

        if search:
            escaped_search = search.replace('"', '\\"')
            cmd += f' --search="{escaped_search}"'

        result = self._execute_wp(cmd)
        categories = json.loads(result)

        logger.debug(f"Found {len(categories)} categories")
        return categories

    def get_post_categories(self, post_id: int) -> List[Dict[str, Any]]:
        """
        Get categories for a specific post

        Args:
            post_id: Post ID

        Returns:
            List of category dictionaries
        """
        cmd = f"post term list {post_id} category --format=json --fields=term_id,name,slug,parent"

        result = self._execute_wp(cmd)
        categories = json.loads(result)

        logger.debug(f"Post {post_id} has {len(categories)} categories")
        return categories

    def get_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get category by name or slug

        Args:
            name: Category name or slug

        Returns:
            Category dictionary or None
        """
        try:
            # Try to get by slug first
            cmd = f"term get category '{name}' --format=json --fields=term_id,name,slug,parent"
            result = self._execute_wp(cmd)
            category = json.loads(result)

            logger.debug(f"Found category: {category}")
            return category
        except WPCLIError:
            # If not found by slug, search by name
            categories = self.list_categories(search=name)

            # Find exact match (case-insensitive)
            for cat in categories:
                if cat['name'].lower() == name.lower() or cat['slug'].lower() == name.lower():
                    return cat

            logger.warning(f"Category '{name}' not found")
            return None

    def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """
        Get category by ID

        Args:
            category_id: Category ID

        Returns:
            Category dictionary or None
        """
        try:
            cmd = f"term get category {category_id} --format=json --fields=term_id,name,slug,parent"
            result = self._execute_wp(cmd)
            category = json.loads(result)

            logger.debug(f"Found category: {category}")
            return category
        except WPCLIError:
            logger.warning(f"Category ID {category_id} not found")
            return None

    def get_config_param(self, param: str) -> Optional[str]:
        """
        Get WordPress configuration parameter

        Args:
            param: Configuration parameter name

        Returns:
            Parameter value or None
        """
        try:
            cmd = f"config get {param}"
            result = self._execute_wp(cmd)
            value = result.strip()

            logger.debug(f"Retrieved config {param}: {value}")
            return value if value else None
        except WPCLIError:
            logger.warning(f"Config parameter '{param}' not found")
            return None

    def set_config_param(self, param: str, value: str) -> bool:
        """
        Set WordPress configuration parameter

        Args:
            param: Configuration parameter name
            value: Parameter value

        Returns:
            True if successful, False otherwise
        """
        try:
            # Escape the value for shell
            escaped_value = value.replace("'", "'\\''")
            cmd = f"config set {param} '{escaped_value}'"
            self._execute_wp(cmd)

            logger.info(f"Set config {param} = {value}")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to set config {param}: {e}")
            return False

    def get_all_config(self) -> Dict[str, str]:
        """
        Get all WordPress configuration parameters

        Returns:
            Dictionary of all config parameters
        """
        try:
            cmd = "config list --format=json"
            result = self._execute_wp(cmd)
            config_data = json.loads(result)

            logger.debug(f"Retrieved {len(config_data)} config parameters")
            return config_data
        except WPCLIError as e:
            logger.error(f"Failed to get all config: {e}")
            return {}

    def create_config(self, params: Dict[str, str], force: bool = False) -> bool:
        """
        Create WordPress wp-config.php file

        Args:
            params: Configuration parameters
            force: Whether to overwrite existing config

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build config creation command
            cmd_parts = ["config create"]

            if force:
                cmd_parts.append("--force")

            # Add parameters
            for key, value in params.items():
                if key.startswith('$'):
                    # Special parameters like $table_prefix
                    escaped_value = value.replace("'", "'\\''")
                    cmd_parts.append(f"--{key}='{escaped_value}'")
                else:
                    escaped_value = value.replace("'", "'\\''")
                    cmd_parts.append(f"--{key}='{escaped_value}'")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info("Created wp-config.php successfully")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to create config: {e}")
            return False

    def get_config_path(self) -> Optional[str]:
        """
        Get WordPress configuration file path

        Returns:
            Config file path or None
        """
        try:
            cmd = "config path"
            result = self._execute_wp(cmd)
            path = result.strip()

            logger.debug(f"Config path: {path}")
            return path if path else None
        except WPCLIError:
            logger.warning("Could not get config path")
            return None

    def get_core_version(self) -> Optional[str]:
        """
        Get WordPress core version

        Returns:
            WordPress version string or None
        """
        try:
            cmd = "core version"
            result = self._execute_wp(cmd)
            version = result.strip()

            logger.debug(f"WordPress version: {version}")
            return version if version else None
        except WPCLIError:
            logger.warning("Could not get WordPress version")
            return None

    def update_core(self, version: Optional[str] = None, force: bool = False) -> bool:
        """
        Update WordPress core

        Args:
            version: Specific version to update to (None for latest)
            force: Force update even if already up to date

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["core", "update"]

            if version:
                cmd_parts.append(f"--version={version}")

            if force:
                cmd_parts.append("--force")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Updated WordPress core to version {version or 'latest'}")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to update WordPress core: {e}")
            return False

    def download_core(self, version: Optional[str] = None, path: Optional[str] = None) -> Optional[str]:
        """
        Download WordPress core

        Args:
            version: Specific version to download (None for latest)
            path: Download path (None for default)

        Returns:
            Download path or None if failed
        """
        try:
            cmd_parts = ["core", "download"]

            if version:
                cmd_parts.append(f"--version={version}")

            if path:
                cmd_parts.append(f"--path={path}")

            cmd = " ".join(cmd_parts)
            result = self._execute_wp(cmd)

            # Extract download path from result
            download_path = result.strip()
            logger.info(f"Downloaded WordPress core to {download_path}")
            return download_path
        except WPCLIError as e:
            logger.error(f"Failed to download WordPress core: {e}")
            return None

    def install_core(self, version: Optional[str] = None, force: bool = False) -> bool:
        """
        Install WordPress core

        Args:
            version: Specific version to install (None for latest)
            force: Force installation even if WordPress exists

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["core", "install"]

            if version:
                cmd_parts.append(f"--version={version}")

            if force:
                cmd_parts.append("--force")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Installed WordPress core version {version or 'latest'}")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to install WordPress core: {e}")
            return False

    def verify_core(self) -> bool:
        """
        Verify WordPress core files

        Returns:
            True if valid, False otherwise
        """
        try:
            cmd = "core verify-checksums"
            self._execute_wp(cmd)

            logger.info("WordPress core files are valid")
            return True
        except WPCLIError as e:
            logger.error(f"WordPress core files are invalid: {e}")
            return False

    def check_core_update(self) -> Optional[Dict[str, Any]]:
        """
        Check for WordPress core updates

        Returns:
            Update information dictionary or None
        """
        try:
            cmd = "core check-update --format=json"
            result = self._execute_wp(cmd)

            if result.strip():
                update_info = json.loads(result)
                logger.debug(f"Core update info: {update_info}")
                return update_info
            else:
                logger.info("WordPress is up to date")
                return {}
        except WPCLIError as e:
            logger.error(f"Failed to check core updates: {e}")
            return None

    def list_cron_events(self) -> List[Dict[str, Any]]:
        """
        List WordPress cron events

        Returns:
            List of cron event dictionaries
        """
        try:
            cmd = "cron event list --format=json"
            result = self._execute_wp(cmd)
            events = json.loads(result)

            logger.debug(f"Retrieved {len(events)} cron events")
            return events
        except WPCLIError as e:
            logger.error(f"Failed to list cron events: {e}")
            return []

    def run_cron(self) -> bool:
        """
        Run WordPress cron events

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = "cron event run --due-now"
            self._execute_wp(cmd)

            logger.info("Executed cron events")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to run cron events: {e}")
            return False

    def schedule_cron_event(self, hook: str, recurrence: str, time: Optional[str] = None, args: Optional[str] = None) -> bool:
        """
        Schedule a WordPress cron event

        Args:
            hook: Hook name
            recurrence: Schedule recurrence
            time: Time for daily/twicedaily schedules
            args: Arguments to pass to hook

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["cron", "event", "schedule", hook, f"--recurrence={recurrence}"]

            if time:
                cmd_parts.append(f"--time={time}")

            if args:
                cmd_parts.append(f"--args={args}")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Scheduled cron event '{hook}' with recurrence '{recurrence}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to schedule cron event: {e}")
            return False

    def delete_cron_event(self, hook: str) -> bool:
        """
        Delete a WordPress cron event

        Args:
            hook: Hook name to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = f"cron event delete {hook}"
            self._execute_wp(cmd)

            logger.info(f"Deleted cron event '{hook}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to delete cron event: {e}")
            return False

    def test_cron(self) -> bool:
        """
        Test WordPress cron system

        Returns:
            True if working, False otherwise
        """
        try:
            cmd = "cron test"
            result = self._execute_wp(cmd)

            # Check if cron is working
            if "SUCCESS" in result or "working" in result.lower():
                logger.info("WordPress cron system is working")
                return True
            else:
                logger.warning("WordPress cron system is not working")
                return False
        except WPCLIError as e:
            logger.error(f"Failed to test cron system: {e}")
            return False

    def list_taxonomies(self) -> List[Dict[str, Any]]:
        """
        List WordPress taxonomies

        Returns:
            List of taxonomy dictionaries
        """
        try:
            cmd = "taxonomy list --format=json"
            result = self._execute_wp(cmd)
            taxonomies = json.loads(result)

            logger.debug(f"Retrieved {len(taxonomies)} taxonomies")
            return taxonomies
        except WPCLIError as e:
            logger.error(f"Failed to list taxonomies: {e}")
            return []

    def get_taxonomy(self, taxonomy: str) -> Optional[Dict[str, Any]]:
        """
        Get WordPress taxonomy information

        Args:
            taxonomy: Taxonomy name

        Returns:
            Taxonomy dictionary or None
        """
        try:
            cmd = f"taxonomy get {taxonomy} --format=json"
            result = self._execute_wp(cmd)
            taxonomy_info = json.loads(result)

            logger.debug(f"Retrieved taxonomy info for {taxonomy}")
            return taxonomy_info
        except WPCLIError:
            logger.warning(f"Taxonomy '{taxonomy}' not found")
            return None

    def list_terms(self, taxonomy: str) -> List[Dict[str, Any]]:
        """
        List WordPress taxonomy terms

        Args:
            taxonomy: Taxonomy name

        Returns:
            List of term dictionaries
        """
        try:
            cmd = f"term list {taxonomy} --format=json"
            result = self._execute_wp(cmd)
            terms = json.loads(result)

            logger.debug(f"Retrieved {len(terms)} terms for {taxonomy}")
            return terms
        except WPCLIError as e:
            logger.error(f"Failed to list terms for {taxonomy}: {e}")
            return []

    def get_term(self, taxonomy: str, term_id: str) -> Optional[Dict[str, Any]]:
        """
        Get WordPress taxonomy term information

        Args:
            taxonomy: Taxonomy name
            term_id: Term ID

        Returns:
            Term dictionary or None
        """
        try:
            cmd = f"term get {taxonomy} {term_id} --format=json"
            result = self._execute_wp(cmd)
            term_info = json.loads(result)

            logger.debug(f"Retrieved term info for {term_id} in {taxonomy}")
            return term_info
        except WPCLIError:
            logger.warning(f"Term '{term_id}' not found in taxonomy '{taxonomy}'")
            return None

    def create_term(self, taxonomy: str, name: str, slug: Optional[str] = None,
                   parent: Optional[str] = None, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a WordPress taxonomy term

        Args:
            taxonomy: Taxonomy name
            name: Term name
            slug: Term slug (optional)
            parent: Parent term ID (optional)
            description: Term description (optional)

        Returns:
            Created term dictionary or None
        """
        try:
            cmd_parts = ["term", "create", taxonomy, f"'{name}'"]

            if slug:
                cmd_parts.append(f"--slug='{slug}'")

            if parent:
                cmd_parts.append(f"--parent={parent}")

            if description:
                escaped_desc = description.replace("'", "'\\''")
                cmd_parts.append(f"--description='{escaped_desc}'")

            cmd_parts.append("--porcelain")
            cmd = " ".join(cmd_parts)
            result = self._execute_wp(cmd)
            term_id = result.strip()

            # Get the created term info
            term_info = self.get_term(taxonomy, term_id)
            logger.info(f"Created term '{name}' in taxonomy '{taxonomy}'")
            return term_info
        except WPCLIError as e:
            logger.error(f"Failed to create term: {e}")
            return None

    def delete_term(self, taxonomy: str, term_id: str) -> bool:
        """
        Delete a WordPress taxonomy term

        Args:
            taxonomy: Taxonomy name
            term_id: Term ID

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = f"term delete {taxonomy} {term_id}"
            self._execute_wp(cmd)

            logger.info(f"Deleted term '{term_id}' from taxonomy '{taxonomy}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to delete term: {e}")
            return False

    def list_widgets(self) -> List[Dict[str, Any]]:
        """
        List WordPress widgets

        Returns:
            List of widget dictionaries
        """
        try:
            cmd = "widget list --format=json"
            result = self._execute_wp(cmd)
            widgets = json.loads(result)

            logger.debug(f"Retrieved {len(widgets)} widgets")
            return widgets
        except WPCLIError as e:
            logger.error(f"Failed to list widgets: {e}")
            return []

    def get_widget(self, widget_id: str) -> Optional[Dict[str, Any]]:
        """
        Get WordPress widget information

        Args:
            widget_id: Widget ID

        Returns:
            Widget dictionary or None
        """
        try:
            cmd = f"widget get {widget_id} --format=json"
            result = self._execute_wp(cmd)
            widget_info = json.loads(result)

            logger.debug(f"Retrieved widget info for {widget_id}")
            return widget_info
        except WPCLIError:
            logger.warning(f"Widget '{widget_id}' not found")
            return None

    def update_widget(self, widget_id: str, options: Dict[str, str]) -> bool:
        """
        Update a WordPress widget

        Args:
            widget_id: Widget ID
            options: Widget options to update

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["widget", "update", widget_id]

            # Add options
            for key, value in options.items():
                escaped_value = str(value).replace("'", "'\\''")
                cmd_parts.append(f"--{key}='{escaped_value}'")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Updated widget '{widget_id}' with options: {list(options.keys())}")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to update widget: {e}")
            return False

    def list_roles(self) -> List[Dict[str, Any]]:
        """
        List WordPress user roles

        Returns:
            List of role dictionaries
        """
        try:
            cmd = "role list --format=json"
            result = self._execute_wp(cmd)
            roles = json.loads(result)

            logger.debug(f"Retrieved {len(roles)} roles")
            return roles
        except WPCLIError as e:
            logger.error(f"Failed to list roles: {e}")
            return []

    def get_role(self, role: str) -> Optional[Dict[str, Any]]:
        """
        Get WordPress role information

        Args:
            role: Role name

        Returns:
            Role dictionary or None
        """
        try:
            cmd = f"role get {role} --format=json"
            result = self._execute_wp(cmd)
            role_info = json.loads(result)

            logger.debug(f"Retrieved role info for {role}")
            return role_info
        except WPCLIError:
            logger.warning(f"Role '{role}' not found")
            return None

    def create_role(self, role_key: str, role_name: str, capabilities: Optional[str] = None) -> bool:
        """
        Create a WordPress user role

        Args:
            role_key: Role key/slug
            role_name: Role display name
            capabilities: Comma-separated list of capabilities

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["role", "create", role_key, f"'{role_name}'"]

            if capabilities:
                cmd_parts.append(f"--capabilities={capabilities}")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Created role '{role_key}' with name '{role_name}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to create role: {e}")
            return False

    def delete_role(self, role: str) -> bool:
        """
        Delete a WordPress user role

        Args:
            role: Role name

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = f"role delete {role}"
            self._execute_wp(cmd)

            logger.info(f"Deleted role '{role}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to delete role: {e}")
            return False

    def scaffold_post_type(self, slug: str, label: Optional[str] = None, 
                          public: Optional[str] = None, has_archive: Optional[str] = None,
                          supports: Optional[str] = None) -> bool:
        """
        Generate a custom post type

        Args:
            slug: Post type slug
            label: Post type label (optional)
            public: Whether public (optional)
            has_archive: Whether has archive (optional)
            supports: Supported features (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["scaffold", "post-type", slug]

            if label:
                cmd_parts.append(f"--label='{label}'")
            if public:
                cmd_parts.append(f"--public={public}")
            if has_archive:
                cmd_parts.append(f"--has_archive={has_archive}")
            if supports:
                cmd_parts.append(f"--supports={supports}")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Generated post type '{slug}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to generate post type: {e}")
            return False

    def scaffold_taxonomy(self, slug: str, label: Optional[str] = None,
                         public: Optional[str] = None, hierarchical: Optional[str] = None,
                         post_types: Optional[str] = None) -> bool:
        """
        Generate a custom taxonomy

        Args:
            slug: Taxonomy slug
            label: Taxonomy label (optional)
            public: Whether public (optional)
            hierarchical: Whether hierarchical (optional)
            post_types: Associated post types (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["scaffold", "taxonomy", slug]

            if label:
                cmd_parts.append(f"--label='{label}'")
            if public:
                cmd_parts.append(f"--public={public}")
            if hierarchical:
                cmd_parts.append(f"--hierarchical={hierarchical}")
            if post_types:
                cmd_parts.append(f"--post_types={post_types}")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Generated taxonomy '{slug}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to generate taxonomy: {e}")
            return False

    def scaffold_plugin(self, slug: str, plugin_name: Optional[str] = None,
                       plugin_uri: Optional[str] = None, author: Optional[str] = None) -> bool:
        """
        Generate a WordPress plugin

        Args:
            slug: Plugin slug
            plugin_name: Plugin name (optional)
            plugin_uri: Plugin URI (optional)
            author: Plugin author (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["scaffold", "plugin", slug]

            if plugin_name:
                cmd_parts.append(f"--plugin_name='{plugin_name}'")
            if plugin_uri:
                cmd_parts.append(f"--plugin_uri='{plugin_uri}'")
            if author:
                cmd_parts.append(f"--author='{author}'")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Generated plugin '{slug}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to generate plugin: {e}")
            return False

    def scaffold_theme(self, slug: str, theme_name: Optional[str] = None,
                      theme_uri: Optional[str] = None, author: Optional[str] = None,
                      author_uri: Optional[str] = None) -> bool:
        """
        Generate a WordPress theme

        Args:
            slug: Theme slug
            theme_name: Theme name (optional)
            theme_uri: Theme URI (optional)
            author: Theme author (optional)
            author_uri: Author URI (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd_parts = ["scaffold", "theme", slug]

            if theme_name:
                cmd_parts.append(f"--theme_name='{theme_name}'")
            if theme_uri:
                cmd_parts.append(f"--theme_uri='{theme_uri}'")
            if author:
                cmd_parts.append(f"--author='{author}'")
            if author_uri:
                cmd_parts.append(f"--author_uri='{author_uri}'")

            cmd = " ".join(cmd_parts)
            self._execute_wp(cmd)

            logger.info(f"Generated theme '{slug}'")
            return True
        except WPCLIError as e:
            logger.error(f"Failed to generate theme: {e}")
            return False
