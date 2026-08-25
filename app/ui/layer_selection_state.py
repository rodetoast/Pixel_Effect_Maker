"""Runtime-only stable-ID layer multi-selection shared by both editors."""

from __future__ import annotations

from PySide6.QtCore import Qt


class LayerSelectionState:
    def __init__(self):
        self.selected_ids:set[str]=set();self.primary_id:str|None=None;self.anchor_id:str|None=None

    def snapshot(self):
        return {"selected_ids":sorted(self.selected_ids),"primary_id":self.primary_id,"anchor_id":self.anchor_id}

    def restore(self,value,ui_ids):
        valid=set(ui_ids);self.selected_ids={str(item) for item in value.get("selected_ids",[]) if str(item) in valid};self.primary_id=value.get("primary_id") if value.get("primary_id") in valid else None;self.anchor_id=value.get("anchor_id") if value.get("anchor_id") in valid else None;self.repair(ui_ids)

    def repair(self,ui_ids,preferred=None,allow_empty=False):
        valid=set(ui_ids);self.selected_ids&=valid
        if preferred in valid:self.primary_id=preferred;self.selected_ids.add(preferred)
        if self.primary_id not in self.selected_ids:self.primary_id=next((item for item in ui_ids if item in self.selected_ids),None)
        if not self.selected_ids and ui_ids and not allow_empty:self.primary_id=preferred if preferred in valid else ui_ids[0];self.selected_ids={self.primary_id}
        if self.anchor_id not in valid:self.anchor_id=self.primary_id
        return self.primary_id

    def clear(self):
        self.selected_ids.clear();self.primary_id=None;self.anchor_id=None

    def click(self,identifier,ui_ids,modifiers=Qt.KeyboardModifier.NoModifier):
        if identifier not in ui_ids:return self.primary_id
        ctrl=bool(modifiers&Qt.KeyboardModifier.ControlModifier);shift=bool(modifiers&Qt.KeyboardModifier.ShiftModifier)
        if shift and self.anchor_id in ui_ids:
            a=ui_ids.index(self.anchor_id);b=ui_ids.index(identifier);values=set(ui_ids[min(a,b):max(a,b)+1])
            self.selected_ids=(self.selected_ids|values) if ctrl else values;self.primary_id=identifier
        elif ctrl:
            if identifier in self.selected_ids and len(self.selected_ids)>1:
                self.selected_ids.remove(identifier)
                if self.primary_id==identifier:self.primary_id=next((item for item in ui_ids if item in self.selected_ids),None)
            else:self.selected_ids.add(identifier);self.primary_id=identifier
            self.anchor_id=identifier
        else:self.selected_ids={identifier};self.primary_id=identifier;self.anchor_id=identifier
        return self.repair(ui_ids)

    def select_all(self,ui_ids):
        self.selected_ids=set(ui_ids);self.repair(ui_ids);return self.primary_id

    def ordered(self,ui_ids):return [item for item in ui_ids if item in self.selected_ids]
