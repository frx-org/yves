from configparser import ConfigParser


def test_parse_config():
    """Test `parse_config` if it creates a default configuration file"""
    import os
    from uuid import uuid4

    from lib.cfg import default_config, parse_config

    def config_to_dict(cfg: ConfigParser) -> dict[str, dict[str, str]]:
        return {section: dict(cfg.items(section)) for section in cfg.sections()}

    dir_path = "/tmp/new/dir/here"
    abs_path = os.path.join(dir_path, f"{uuid4().hex}")
    default_cfg = default_config()
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    assert not os.path.exists(abs_path)

    cfg = parse_config(abs_path)
    assert os.path.exists(abs_path)

    assert config_to_dict(default_cfg) == config_to_dict(cfg)
