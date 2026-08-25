from app.ui.hierarchy_display import context_action_states


def test_leaf_context_actions_follow_parent_and_lock_state():
    free=context_action_states("leaf",1,False,False);parented=context_action_states("leaf",1,False,True);locked=context_action_states("leaf",1,True,True)
    assert free["set_parent"] and not free["clear_parent"]
    assert parented["clear_parent"] and parented["reorder"]
    assert not locked["delete"] and not locked["set_parent"] and not locked["reorder"]


def test_group_and_multiselect_actions_are_type_aware():
    group=context_action_states("group",1,False,False);multi=context_action_states("leaf",3,False,False)
    assert group["ungroup"] and not group["set_parent"] and not group["group"]
    assert multi["group"] and not multi["set_parent"]
