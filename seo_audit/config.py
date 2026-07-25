"""Configuration module for customizable SEO audit thresholds.

Loads settings from a .seoauditrc.yaml file if present, otherwise falls
back to sensible defaults. All check functions that have tunable thresholds
accept these values as parameters.

Usage:
    from seo_audit.config import load_config, DEFAULTS
    config = load_config()
    # config is a dict with keys: title_min_length, title_max_length, etc.

Default configurable values:
    thresholds:
        title_min_length: 30
        title_max_length: 60
        meta_description_min_length: 120
        meta_description_max_length: 160
        word_count_minimum: 300
    crawl:
        max_pages: 20
        max_depth: 2
    general:
        timeout: 10
"""

import os
from pathlib import Path

DEFAULTS = {
    "thresholds": {
        "title_min_length": 30,
        "title_max_length": 60,
        "meta_description_min_length": 120,
        "meta_description_max_length": 160,
        "word_count_minimum": 300,
    },
    "crawl": {
        "max_pages": 20,
        "max_depth": 2,
    },
    "general": {
        "timeout": 10,
    },
}


def _deep_merge(base, override):
    """Recursively merge override dict into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path=".seoauditrc.yaml"):
    """Load configuration from a YAML file, falling back to defaults.

    Args:
        path: Path to the YAML config file. Defaults to .seoauditrc.yaml
            in the current working directory.

    Returns:
        A dict with all configuration values. Keys not present in the YAML
        file are filled in from DEFAULTS.
    """
    config = DEFAULTS.copy()

    # Check for config file in multiple locations.
    search_paths = [
        path,
        os.path.expanduser("~/.seoauditrc.yaml"),
        os.path.expanduser("~/.config/seo-audit/config.yaml"),
    ]

    yaml_path = None
    for candidate in search_paths:
        if os.path.isfile(candidate):
            yaml_path = candidate
            break

    if yaml_path is None:
        # Return a deep copy of defaults.
        return _deep_merge(DEFAULTS, {})

    try:
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f)
        if user_config:
            config = _deep_merge(config, user_config)
    except ImportError:
        # PyYAML not installed — fall back to defaults.
        pass
    except Exception:
        # Malformed YAML or read error — fall back to defaults.
        pass

    return config


def get_thresholds(config):
    """Extract threshold values from config for convenient access.

    Args:
        config: Config dict from load_config().

    Returns:
        Dict with flat keys: title_min_length, title_max_length, etc.
    """
    t = config.get("thresholds", {})
    return {
        "title_min_length": t.get("title_min_length", DEFAULTS["thresholds"]["title_min_length"]),
        "title_max_length": t.get("title_max_length", DEFAULTS["thresholds"]["title_max_length"]),
        "meta_description_min_length": t.get("meta_description_min_length", DEFAULTS["thresholds"]["meta_description_min_length"]),
        "meta_description_max_length": t.get("meta_description_max_length", DEFAULTS["thresholds"]["meta_description_max_length"]),
        "word_count_minimum": t.get("word_count_minimum", DEFAULTS["thresholds"]["word_count_minimum"]),
    }


def get_crawl_settings(config):
    """Extract crawl settings from config.

    Args:
        config: Config dict from load_config().

    Returns:
        Dict with keys: max_pages, max_depth.
    """
    c = config.get("crawl", {})
    return {
        "max_pages": c.get("max_pages", DEFAULTS["crawl"]["max_pages"]),
        "max_depth": c.get("max_depth", DEFAULTS["crawl"]["max_depth"]),
    }
