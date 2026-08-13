# Layer Group Hierarchy (v0.0.07)

Pixel Effect Maker uses a deliberately shallow hierarchy. A root contains individual leaf layers and groups; a group contains leaf layer IDs only. Nested groups, group transforms, parenting, inherited coordinates, group keyframes, and group-generated pixel layers are outside v0.0.07.

The serialized v11 representation stores `groups` plus `root_order` for each Resource Composition, and `effect_layer_groups` plus `effect_root_order` for the Effect Editor. Existing leaf arrays remain the source of layer content. The model synchronizes those flat arrays to the hierarchy's flattened order, so older renderer and editor paths retain the established back-to-front convention.

Runtime collapse state and selection are not serialized. A v10 project migrates to a root list of its existing leaves. When v11 hierarchy metadata contains unknown, duplicate, or conflicting references, loading keeps the first valid reference and appends every otherwise orphaned real leaf in its original flat order. Empty valid groups are retained.

Visibility and lock are effective parent policies: a hidden group suppresses its leaves in preview and final rendering, and a locked group protects child editing, keyframes, reorder, and deletion. Solo is intentionally preview-only. A group or any soloed leaf activates preview isolation; export and Bake continue to use ordinary visibility.
