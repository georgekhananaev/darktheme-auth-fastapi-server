import os
import yaml
from typing import Dict, Any, Optional


class Config:
    """
    Singleton class for application configuration.
    Loads and caches configuration from config.yaml.
    """
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._load_config()
        return cls._instance

    @classmethod
    def _load_config(cls):
        """Load configuration from config.yaml file"""
        try:
            # Determine the root directory of the project
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(root_dir, 'config.yaml')
            
            # Load the configuration file
            with open(config_path, 'r') as file:
                cls._config = yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            cls._config = {}

    @classmethod
    def get(cls, section: str = None, key: str = None, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section: The section of the configuration to get
            key: The key within the section to get
            default: The default value to return if the section or key is not found
            
        Returns:
            The configuration value, or the default value if not found
        """
        if cls._config is None:
            cls._load_config()
            
        if section is None:
            return cls._config
            
        section_value = cls._config.get(section, {})
        
        if key is None:
            return section_value
            
        return section_value.get(key, default)

    @classmethod
    def is_redis_enabled(cls) -> bool:
        """
        Check if Redis is enabled in the configuration.
        
        Returns:
            bool: True if Redis is enabled, False otherwise
        """
        return cls.get('redis', 'enabled', True)
    
    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """
        Get Redis configuration.
        
        Returns:
            Dict: Redis configuration
        """
        return cls.get('redis', default={})
    
    @classmethod
    def get_server_config(cls) -> Dict[str, Any]:
        """
        Get server configuration.
        
        Returns:
            Dict: Server configuration
        """
        return cls.get('server', default={})
    
    @classmethod
    def get_cors_config(cls) -> Dict[str, Any]:
        """
        Get CORS configuration.
        
        Returns:
            Dict: CORS configuration
        """
        return cls.get('cors', default={})
    
    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """
        Get API configuration.
        
        Returns:
            Dict: API configuration
        """
        return cls.get('api', default={})
    
    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """
        Get logging configuration.
        
        Returns:
            Dict: Logging configuration including settings for all log types
        """
        return cls.get('logging', default={
            'directory': './logs',
            'max_size': 10485760,  # 10MB
            'backup_count': 5,
            'max_records': 10000,
            'access': {
                'enabled': True,
                'level': 'INFO',
                'filename': 'access.log',
                'format': '[%(asctime)s] [%(levelname)s] [%(client_ip)s] [%(username)s] %(message)s'
            },
            'security': {
                'enabled': True,
                'level': 'INFO',
                'filename': 'security.log',
                'format': '[%(asctime)s] [%(levelname)s] [%(client_ip)s] [%(username)s] %(message)s'
            },
            'system': {
                'enabled': True,
                'level': 'INFO',
                'filename': 'system.log',
                'format': '[%(asctime)s] [%(levelname)s] [%(module)s] [%(funcName)s] %(message)s'
            }
        })
    
    @classmethod
    def get_server_title(cls) -> str:
        """
        Get server title.
        
        Returns:
            str: Server title
        """
        return cls.get('server', 'title', "darktheme-auth-fastapi-server")
    
    @classmethod
    def get_api_prefix(cls) -> str:
        """
        Get API prefix.
        
        Returns:
            str: API prefix
        """
        return cls.get('api', 'prefix', '/api/v1')


# Create a global instance for convenient access
config = Config()