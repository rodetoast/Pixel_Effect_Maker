"""Shared, read-only eligibility for the existing one-level grouping commands."""
def effect_group_reasons(project, identifiers):
    selected=set(identifiers)
    leaves={layer.id:layer for layer in project.effect_resource_layers}
    groups={group.id:group for group in project.effect_layer_groups}
    def locked(identifier):
        if identifier in leaves:return project.effect_effective_locked(leaves[identifier])
        group=groups.get(identifier)
        return bool(group and (group.locked or any(locked(child) for child in group.children)))
    if len(selected)<2:group_reason="count"
    elif not selected.issubset(leaves):group_reason="group_selected"
    elif any(project.effect_parent_group(identifier) for identifier in selected):group_reason="membership"
    elif any(locked(identifier) for identifier in selected):group_reason="locked"
    else:
        indices=[i for i,node in enumerate(project.effect_root_order) if node["type"]=="layer" and node["id"] in selected]
        group_reason=None if len(indices)==len(selected) and indices==list(range(min(indices),max(indices)+1)) else "contiguous"
    group=groups.get(next(iter(selected))) if len(selected)==1 else None
    ungroup_reason="select_group" if group is None else "locked" if locked(group.id) else None
    return group_reason,ungroup_reason

def effect_group_reason_text(reason,ko):
    messages={
        "count":("Select at least two adjacent root layers.","루트에서 인접한 레이어를 2개 이상 선택하세요."),
        "group_selected":("Select layers, not a group. Nested groups are not supported.","그룹이 아닌 레이어를 선택하세요. 중첩 그룹은 지원하지 않습니다."),
        "membership":("Ungroup existing members first. Nested/cross-group grouping is not supported.","기존 그룹을 먼저 해제하세요. 중첩·그룹 간 묶기는 지원하지 않습니다."),
        "locked":("Unlock the group and its selected/member layers first.","그룹과 선택·멤버 레이어의 잠금을 먼저 해제하세요."),
        "contiguous":("Select adjacent root layers to preserve draw order.","그리기 순서를 유지하려면 루트의 인접한 레이어를 선택하세요."),
        "select_group":("Select one group header to ungroup, not its member layers.","멤버 레이어가 아닌 그룹 헤더 하나를 선택하여 해제하세요."),
    }
    return messages[reason][int(ko)] if reason else ""
