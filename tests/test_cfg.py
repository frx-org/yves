from configparser import ConfigParser


def test_parse_config(tmpdir):
    """Test `parse_config` if it creates a default configuration file"""
    import os
    from uuid import uuid4

    from lib.cfg import default_config, parse_config

    def config_to_dict(cfg: ConfigParser) -> dict[str, dict[str, str]]:
        return {section: dict(cfg.items(section)) for section in cfg.sections()}

    abs_path = tmpdir / f"{uuid4().hex}"
    default_cfg = default_config()

    cfg = parse_config(abs_path)
    assert os.path.exists(abs_path)

    assert config_to_dict(default_cfg) == config_to_dict(cfg)
