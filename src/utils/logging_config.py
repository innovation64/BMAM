import logging
import logging.handlers
import os
from typing import Dict, Any

def setup_logging(config: Dict[str, Any]):
    """Setup logging configuration for the MA-CMM system"""
    
    log_level = config.get('level', 'INFO').upper()
    log_format = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = config.get('file', 'logs/ma-cmm.log')
    max_size = config.get('max_size', '10MB')
    backup_count = config.get('backup_count', 5)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Convert max_size to bytes
    if isinstance(max_size, str):
        if max_size.endswith('MB'):
            max_bytes = int(max_size[:-2]) * 1024 * 1024
        elif max_size.endswith('KB'):
            max_bytes = int(max_size[:-2]) * 1024
        else:
            max_bytes = int(max_size)
    else:
        max_bytes = max_size
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels for components
    logging.getLogger('ma-cmm').setLevel(getattr(logging, log_level))
    logging.getLogger('ma-cmm.orchestrator').setLevel(getattr(logging, log_level))
    logging.getLogger('ma-cmm.memory').setLevel(getattr(logging, log_level))
    logging.getLogger('ma-cmm.api_client').setLevel(getattr(logging, log_level))
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    
    logging.info("Logging configured successfully")


class LoggingContext:
    """Context manager for temporary logging configuration"""
    
    def __init__(self, logger_name: str, level: str = 'DEBUG'):
        self.logger_name = logger_name
        self.level = level
        self.original_level = None
    
    def __enter__(self):
        logger = logging.getLogger(self.logger_name)
        self.original_level = logger.level
        logger.setLevel(getattr(logging, self.level.upper()))
        return logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logger = logging.getLogger(self.logger_name)
        if self.original_level is not None:
            logger.setLevel(self.original_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(f"ma-cmm.{name}")


class PerformanceLogger:
    """Logger for tracking performance metrics"""
    
    def __init__(self, name: str = "performance"):
        self.logger = get_logger(name)
        self.metrics = {}
    
    def log_metric(self, metric_name: str, value: float, unit: str = ""):
        """Log a performance metric"""
        self.metrics[metric_name] = value
        self.logger.info(f"METRIC: {metric_name}={value}{unit}")
    
    def log_timing(self, operation: str, duration: float):
        """Log operation timing"""
        self.log_metric(f"{operation}_duration", duration, "s")
    
    def log_memory_usage(self, component: str, size: int):
        """Log memory usage"""
        self.log_metric(f"{component}_memory", size, "bytes")
    
    def log_api_call(self, endpoint: str, cost: float, duration: float):
        """Log API call metrics"""
        self.logger.info(f"API_CALL: {endpoint} cost=${cost:.4f} duration={duration:.2f}s")
    
    def get_metrics(self) -> Dict[str, float]:
        """Get all logged metrics"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics.clear()