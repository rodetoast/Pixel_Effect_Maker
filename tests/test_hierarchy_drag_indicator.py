from app.ui.hierarchy_display import DROP_AFTER,DROP_BEFORE,DROP_INTO,classify_drop_zone,drop_is_allowed,resolve_drop_target


def test_group_drop_zone_has_distinct_before_into_after_regions():
    assert classify_drop_zone("group",1,40)==DROP_BEFORE
    assert classify_drop_zone("group",20,40)==DROP_INTO
    assert classify_drop_zone("group",39,40)==DROP_AFTER
    assert classify_drop_zone("leaf",10,40)==DROP_BEFORE and classify_drop_zone("leaf",30,40)==DROP_AFTER


def test_drop_target_handles_into_empty_group_and_batch_index_adjustment():
    kinds={"g":"group","a":"leaf","b":"leaf","c":"leaf"};parents={"g":None,"a":None,"b":None,"c":None};siblings={None:["g","a","b","c"],"g":[]}
    assert resolve_drop_target("g",DROP_INTO,kinds,parents,siblings,{"a","b"})==("g",0)
    assert resolve_drop_target("c",DROP_AFTER,kinds,parents,siblings,{"a","b"})==(None,2)


def test_invalid_nested_locked_and_mixed_parent_targets_are_rejected():
    kinds={"g":"group","h":"group","a":"leaf","b":"leaf"};parents={"g":None,"h":None,"a":None,"b":"g"}
    assert not drop_is_allowed({"h"},"g",DROP_INTO,kinds,parents,set())
    assert not drop_is_allowed({"a"},"g",DROP_INTO,kinds,parents,{"g"})
    assert not drop_is_allowed({"a","b"},"h",DROP_BEFORE,kinds,parents,set())
