import os
import pytest
from pytest import raises

from betterconf import Config
from betterconf import field
from betterconf.caster import AbstractCaster, ConstantCaster, IntCaster
from betterconf.caster import to_bool
from betterconf.caster import to_int
from betterconf.config import AbstractProvider, Field
from betterconf.config import VariableNotFoundError

VAR_1 = "hello"
VAR_1_VALUE = "hello!#"


def fixture_config():
    class TestConfig(Config):
        debug = field('DEBUG', default=False, caster=to_bool)

        class Sub1Config:
            class Sub2Config:
                config_1 = field(default='base.mail.com')
                config_2 = field(default='465')
                config_3 = field(default='test')

    class ProdConfig(TestConfig):
        __prefix__ = 'PROD'

        class Sub1Config(TestConfig.Sub1Config):
            class Sub2Config(TestConfig.Sub1Config.Sub2Config):
                config_1 = field(default='prod.mail.com')
                config_2 = field(default='465')

    return TestConfig, ProdConfig


def test_not_exist():
    class ConfigBad(Config):
        var1 = field(VAR_1)

    with pytest.raises(VariableNotFoundError):
        ConfigBad()


def test_exist():
    os.environ[VAR_1] = VAR_1_VALUE

    class ConfigGood(Config):
        var1 = field(VAR_1)

    cfg = ConfigGood()
    assert cfg.var1 == VAR_1_VALUE


def test_default():
    class ConfigDefault(Config):
        var1 = field("var_1", default="var_1 value")
        var2 = field("var_2", default=lambda: "callable var_2")

    cfg = ConfigDefault()
    assert cfg.var1 == "var_1 value"
    assert cfg.var2 == "callable var_2"


def test_override():
    class ConfigOverride(Config):
        var1 = field("var_1", default=1)

    cfg = ConfigOverride(var1=100000)
    assert cfg.var1 == 100000


def test_own_provider():
    class MyProvider(AbstractProvider):
        def get(self, name: str):
            return name  # just return name of filed =)

    provider = MyProvider()

    class ConfigWithMyProvider(Config):
        var1 = field("var_1", provider=provider)

    cfg = ConfigWithMyProvider()
    assert cfg.var1 == "var_1"


def test_bundled_casters():
    os.environ["boolean"] = "true"
    os.environ["integer"] = "-543"

    class MyConfig(Config):
        boolean = field("boolean", caster=to_bool)
        integer = field("integer", caster=to_int)

    cfg = MyConfig()
    assert cfg.boolean is True
    assert cfg.integer == -543


def test_own_caster():
    os.environ["text-with-dashes"] = "text-with-dashes"

    class DashToDotCaster(AbstractCaster):
        def cast(self, val: str):
            val = val.replace("-", ".")
            return val

    to_dot = DashToDotCaster()

    class MyConfig(Config):
        text = field("text-with-dashes", caster=to_dot)

    cfg = MyConfig()
    assert cfg.text == "text.with.dashes"


def test_to_dict():
    config = fixture_config()[1]

    assert config.to_dict() == {
        'Sub1Config': {
            'Sub2Config': {
                'config_1': 'prod.mail.com',
                'config_2': '465',
                'config_3': 'test'
            },
        },
        'debug': False
    }


def test_default_name_field():
    os.environ['DEBUG'] = 'true'
    os.environ['APP_SUB1CONFIG_SUB2CONFIG_CONFIG_1'] = 'test.mail.com'
    os.environ['PROD_SUB1CONFIG_SUB2CONFIG_CONFIG_2'] = '100202'

    test_config, prod_config = fixture_config()

    assert test_config.debug is True
    assert test_config.Sub1Config.Sub2Config.config_1 == 'test.mail.com'
    assert prod_config.Sub1Config.Sub2Config.config_2 == '100202'


def test_required_fields():
    class TestConfig(Config):
        config_1 = field()

    config = TestConfig
    with raises(VariableNotFoundError):
        config.required_fields()


def test_fiend_name_is_none():
    with raises(VariableNotFoundError):
        Field().value()


def test_raise_abstract_provider():
    with raises(NotImplementedError):
        AbstractProvider().get('test')


def test_raise_abstract_caster():
    with raises(NotImplementedError):
        AbstractCaster().cast('test')


def test_constant_caster():
    constant_caster = ConstantCaster()

    constant_caster.ABLE_TO_CAST = {
        ('key_1', 'key_2'): 'test'
    }
    assert constant_caster.cast('key_2') == 'test'

    constant_caster.ABLE_TO_CAST = {
        'key_1': 'test'
    }
    assert constant_caster.cast('Key_1') == 'test'

    assert constant_caster.cast('key') == 'key'


def test_raises_int_caster():
    int_caster = IntCaster()
    assert int_caster.cast('test') == 'test'
