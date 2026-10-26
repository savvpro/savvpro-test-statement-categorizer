from app.domain.models import Category
from app.learning.repository import JsonFileMerchantRuleRepository, MerchantRule


def test_json_repository_persists_across_instances(tmp_path):
    path = tmp_path / "rules.json"
    JsonFileMerchantRuleRepository(str(path)).save(MerchantRule("JOES CAFE", Category.TRAVEL))
    reloaded = JsonFileMerchantRuleRepository(str(path))
    assert reloaded.get("JOES CAFE").category == Category.TRAVEL
    assert reloaded.delete("JOES CAFE") and JsonFileMerchantRuleRepository(str(path)).list() == []
