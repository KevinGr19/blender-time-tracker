import os, json
import bpy

#region Properties
SCENE_PROP_NAME = "custom_time_tracking"

class TimeTrackingProps(bpy.types.PropertyGroup):
    is_tracking: bpy.props.BoolProperty(
        name="Enable time tracking",
        description="Activates global time tracking",
        default=True
    ) #type: ignore

    inactivity_time: bpy.props.IntProperty(
        name="Inactivity threshold",
        description="Number of minutes until the timer pauses for inactivity",
        default=20,
        min=1,
    ) #type: ignore

def get_props() -> TimeTrackingProps:
    return getattr(bpy.context.scene, SCENE_PROP_NAME)

def register_props():
    bpy.utils.register_class(TimeTrackingProps)
    setattr(bpy.types.Scene, SCENE_PROP_NAME, bpy.props.PointerProperty(type=TimeTrackingProps))

def unregister_props():
    delattr(bpy.types.Scene, SCENE_PROP_NAME)
    bpy.utils.unregister_class(TimeTrackingProps)
#endregion

#region Timer
class Timer:
    def __init__(self):
        self.session_time:int = 0
        self.total_time:int = 0
        self.inactivity_countdown:int = 0

    def add_seconds(self, seconds:int):
        self.session_time += seconds
        self.total_time += seconds

    def set_inactivity_countdown(self, minutes:int):
        self.inactivity_countdown = minutes * 60

timer = Timer()

class TIMETRACKER_OT_modalActivityTrack(bpy.types.Operator):
    bl_idname = "tt.modal_activity_track"
    bl_label = "Modal Track Activity"
    
    def invoke(self, context, event):
        return self.execute(context)
    
    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        props = get_props()
        timer.set_inactivity_countdown(props.inactivity_time)
        restart_modal_activity_track()
        return {'CANCELLED'}
    
def start_modal_activity_track():
    bpy.ops.tt.modal_activity_track()

def restart_modal_activity_track(delay:float=15):
    bpy.app.timers.register(start_modal_activity_track, first_interval=delay)

def timer_func() -> float:
    props = get_props()
    if props.is_tracking and timer.inactivity_countdown > 0:
       timer.add_seconds(1)
       timer.inactivity_countdown -= 1
    return 1.0

def register_timer():
    bpy.utils.register_class(TIMETRACKER_OT_modalActivityTrack)
    bpy.app.timers.register(timer_func, first_interval=1.0, persistent=True)

def unregister_timer():
    bpy.app.timers.unregister(timer_func)
    bpy.utils.unregister_class(TIMETRACKER_OT_modalActivityTrack)
#endregion

#region UI
def pretty_time(seconds:int):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h>99: return f"{h}h"
    elif h>0: return f"{h}h {m}m"
    else: return f"{m}m {s}s"

class TOPBAR_MT_timetracker(bpy.types.Menu):
    bl_idname = "TOPBAR_MT_timetracker"
    bl_label = "Time"

    def draw(self, context):
        props = get_props()
        layout = self.layout

        layout.label(text=f"Total time: {pretty_time(timer.total_time)}", icon="TIME")
        layout.label(text=f"Session time: {pretty_time(timer.session_time)}", icon="SORTTIME")
        layout.separator()
        layout.prop(props, "is_tracking")
        layout.operator("wm.path_open", text="Show data in File Explorer", icon='FILE_FOLDER').filepath = os.path.dirname(DATA_PATH)

def draw_timetracker_menu(self, context):
    self.layout.menu(TOPBAR_MT_timetracker.bl_idname)

def register_ui():
    bpy.utils.register_class(TOPBAR_MT_timetracker)
    bpy.types.TOPBAR_MT_editor_menus.append(draw_timetracker_menu)

def unregister_ui():
    bpy.types.TOPBAR_MT_editor_menus.remove(draw_timetracker_menu)
    bpy.utils.unregister_class(TOPBAR_MT_timetracker)
#endregion

#region Load/Save
DATA_PATH = os.path.join(bpy.utils.extension_path_user(package=__package__, path="data"), "time.json")

def load_from_json():
    props = get_props()

    if os.path.exists(DATA_PATH):
        try:
            data = json.load(open(DATA_PATH, 'r'))
        except Exception as e:
            print(f'Could not load json data : {e}')
            raise
        
        assert hasattr(bpy.context, "scene")
        props.is_tracking = data['is_tracking']
        props.inactivity_time = data['inactivity_time']
        timer.total_time = data['total_time']

    timer.set_inactivity_countdown(props.inactivity_time)
    start_modal_activity_track()

def save_to_json():
    try:
        props = get_props()
        data = {
            'is_tracking': props.is_tracking,
            'inactivity_time': props.inactivity_time,
            'total_time': timer.total_time,
        }

        if os.path.exists(DATA_PATH):
            old_data = json.load(open(DATA_PATH, 'r'))
            data['total_time'] = max(old_data['total_time'], data['total_time'])

        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        json.dump(data, open(DATA_PATH, 'w'))
    except Exception as e:
        print(f'Could not save time data : {e}')
        raise

@bpy.app.handlers.persistent
def save_handler(scene):
    save_to_json()
#endregion

def register():
    register_props()
    register_timer()
    register_ui()
    bpy.app.timers.register(load_from_json)
    bpy.app.handlers.save_pre.append(save_handler)

def unregister():
    bpy.app.handlers.save_pre.remove(save_handler)
    try: save_to_json()
    except: pass
    
    unregister_ui()
    unregister_timer()
    unregister_props()