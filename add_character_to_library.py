import maya.cmds as cmds
import maya.mel as mel
import xml.etree.ElementTree as xmlET

def lock_node(node_name, translation=True, rotation=True, scale=True):
    channels = []
    if translation:
        channels.extend(["tx", "ty", "tz"])
    if rotation:
        channels.extend(["rx", "ry", "rz"])
    if scale:
        channels.extend(["sx", "sy", "sz"])
        
    for channel in channels:
        cmds.setAttr(f"{node_name}.{channel}", lock=True)

def import_fbx_rig(fbx_path):
    cmds.file(newFile=True, force=True)
    fbx_name = fbx_path.split("\\")[-1]
    character_name = fbx_name.split(".")[0]
    cmds.file(fbx_path, i=True)
    return character_name


def structure_rig():
    # Delete lights coming with Autodesk Character Generator rigs
    light_grp = cmds.ls("Lights", type="transform")
    cmds.delete(light_grp)
    
    # Create rig base structure
    root_grp = cmds.createNode("transform", name=character_name)
    lock_node(root_grp)
    geo_grp = cmds.createNode("transform", name="geo", parent=root_grp)
    lock_node(geo_grp)
    
    skeleton_grp = cmds.createNode("transform", name="skeleton", parent=root_grp)
    lock_node(skeleton_grp)
    ctrl_grp = cmds.createNode("transform", name="ctrl", parent=root_grp)
    lock_node(ctrl_grp)
    
    master_ctrl = cmds.circle(name="master_ctrl", normal=[0,1,0], radius=50)[0]
    offset_ctrl_grp = cmds.createNode("transform", name="offset_ctrl_grp", parent=master_ctrl)
    lock_node(offset_ctrl_grp)
    offset_ctrl = cmds.circle(name="offset_ctrl", normal=[0,1,0], radius=50*0.75)[0]
    cmds.parent(offset_ctrl, offset_ctrl_grp)
    
    rig_master_grp = cmds.ls("master", type="transform")
    cmds.parent(rig_master_grp, skeleton_grp)
    cmds.parent(master_ctrl, ctrl_grp)
    
    # Group geometry according to resolution
    resolutions = ["crowd", "low", "mid", "high"]
    for res in resolutions:
        res_prefix = f"{res[0]}_*"
        res_meshes = cmds.ls(res_prefix, type="transform")
        main_mesh = cmds.ls(f"*{res.capitalize()}Res", type="transform", noIntermediate=True)
        res_meshes.extend(main_mesh)
        if not res_meshes:
            continue
        res_geo_grp = cmds.createNode("transform", name=res, parent=geo_grp)
        lock_node(res_geo_grp)
        cmds.parent(res_meshes, res_geo_grp)
    
    # Create visibility switch
    cmds.addAttr(master_ctrl, longName="GeoRes", attributeType="enum", enumName="".join([res + "=" + str(idx) + ":" for idx, res in enumerate(resolutions)]))
    cmds.setAttr(f"{master_ctrl}.GeoRes", keyable=False, channelBox=True)
    
    for idx, res in enumerate(resolutions):
        res_geo_grp = cmds.ls(res, type="transform")[0]
        res_condition = cmds.shadingNode("condition", asUtility=True)
        cmds.setAttr(f"{res_condition}.secondTerm", idx)
        cmds.setAttr(f"{res_condition}.colorIfTrueR", 1)
        cmds.setAttr(f"{res_condition}.colorIfFalseR", 0)
        cmds.connectAttr(f"{master_ctrl}.GeoRes", f"{res_condition}.firstTerm", force=True)
        cmds.connectAttr(f"{res_condition}.outColor.outColorR", f"{res_geo_grp}.visibility", force=True)


def add_acg_rig_to_library():
    fbx_path = "C:\\Users\\COVISE\\Desktop\\Character_workflow_test\\character\\_import\\Wanda\\Wanda.fbx"
    character_name = import_fbx_rig(fbx_path)
    structure_rig()
    create_hik_rig()
    char_def_dict = character_definition_from_xml("C:\\Users\\COVISE\\Desktop\\Character_workflow_test\\script\\CharacterGenerator_CharacterDefinition.xml")
    apply_joint_mapping(char_def_dict, rig_name)
    cmds.evalDeferred(create_control_rig)
    save_rig("C:\\Users\\COVISE\\Desktop\\Character_workflow_test")


def create_hik_rig():
    loaded_plugins = cmds.pluginInfo(query=True, listPlugins=True)
    if "mayaHIK" not in loaded_plugins:
        cmds.loadPlugin("mayaHIK")
    
    mel.eval("HIKCharacterControlsTool ;")
    mel.eval("hikCreateDefinition();")
    rig_name = f"Rig_{character_name}"
    
    cmds.rename(cmds.ls("Character1")[0], rig_name)


def character_definition_from_xml(xml_path):
    with open(xml_path, "r", encoding="utf-8") as xml_definition:
        character_xml_data = xml_definition.read()
    root = xmlET.fromstring(character_xml_data)
    char_def_dict = {el.get("key"): el.get("value") for el in root.findall("./match_list/item")}
    return char_def_dict


def apply_joint_mapping(char_def_dict, rig_name):
    for idx, (hik_joint, rig_joint) in enumerate(char_def_dict.items()):
        if rig_joint:
            mel.eval(f'setCharacterObject("{rig_joint}","{rig_name}",{idx},0);')
    

def create_control_rig():
    mel.eval("hikCreateControlRig;")

    hik_ctrl_root = cmds.ls(f"{rig_name}_Ctrl_Reference", type="transform")
    cmds.parent(hik_ctrl_root, offset_ctrl)
    
    controller_radius = {
        "HipsEffector": 20,
        "ChestEndEffector": 20,
        "HeadEffector": 13,
        "LeftHipEffector": 15,
        "RightHipEffector": 15,
        "LeftShoulderEffector": 12,
        "RightShoulderEffector": 12,
        "LeftElbowEffector": 5,
        "RightElbowEffector": 5, 
        "LeftWristEffector": 8,
        "RightWristEffector": 8,
        "LeftAnkleEffector": 8,
        "RightAnkleEffector": 8,
        "LeftKneeEffector": 5,
        "RightKneeEffector": 5,
        "LeftFootEffector": 5,
        "RightFootEffector": 5,
        "Fingers": 3.5,
    }
    
    for effector, finger_radius in controller_radius.items():
        if effector == "Fingers":
            finger_effectors = cmds.ls(f"{rig_name}_Ctrl_LeftHand*Effector")
            finger_effectors.extend(cmds.ls(f"{rig_name}_Ctrl_RightHand*Effector"))
            hand_effectors = cmds.ls(f"{rig_name}_Ctrl_*HandEffector")
            finger_effectors = list(set(finger_effectors) - set(hand_effectors))
            for finger in finger_effectors:
                cmds.setAttr(f"{finger}.radius", finger_radius)
        else:
            cmds.setAttr(f"{rig_name}_Ctrl_{effector}.radius", finger_radius)


def save_rig(library_output_dir):
    cmds.file(rename=f"{library_output_dir}/{character_name}.mb")
    cmds.file(save=True, force=True)


add_acg_rig_to_library()


# ToDo: Find geo not present in all resolution, and instanciate into groups where missing
# ToDo: How to handle if a geo LOD level is missing?
# ToDo: Create according library structure when saving, including all textures in correct directory
# ToDo: Relink all textures to the one in the dir (also check how to do this if they are only present in the fbx file)
# ToDo: Check if character with this name already exists
# ToDo: Logging
# ToDo: Cleanup

# ToDo: Accept input: dir, zip (most important!) and fbx
# ToDo: Write batch entry point