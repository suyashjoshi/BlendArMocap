import bpy
from .. import input_manager


class UI_transfer_anim_button(bpy.types.Operator):
    bl_label = "Transfer Animation"
    bl_idname = "button.cgt_transfer_animation_button"
    bl_description = "Transfer driver animation to cgt_rig"

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT'}

    def execute(self, context):
        input_manager.transfer_animation()
        return {'FINISHED'}


class UI_toggle_drivers_button(bpy.types.Operator):
    bl_label = "Toggle Drivers"
    bl_idname = "button.cgt_toggle_drivers_button"
    bl_description = "Toggle drivers to improve performance while motion capturing"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        input_manager.toggle_drivers()
        return {'FINISHED'}


class WM_modal_detection_operator(bpy.types.Operator):
    bl_label = "Feature Detection Operator"
    bl_idname = "wm.cgt_feature_detection_operator"
    bl_description = "Detect solution in Stream."

    _timer = None
    detection_handler = None
    user = None

    def execute(self, context):
        """ Runs movie or stream detection depending on user input. """
        self.user = context.scene.m_cgtinker_mediapipe  # noqa

        # hacky way to check if operator is running
        if self.user.detection_operator_running is True:
            self.user.detection_operator_running = False
            return {'FINISHED'}
        else:
            self.user.detection_operator_running = True

        # create a detection handler
        from ...main import DetectionHandler
        detection_type = self.user.enum_detection_type
        self.detection_handler = DetectionHandler(detection_type, "BPY")

        # initialize detector using user inputs
        frame_start = bpy.context.scene.frame_start
        if self.user.detection_input_type == 'movie':
            mov_path = self.user.mov_data_path
            self.detection_handler.init_detector(mov_path, "sd", 0, frame_start, 1, "movie")
        else:
            camera_index = self.user.webcam_input_device
            dimensions = self.user.enum_stream_dim
            backend = int(self.user.enum_stream_type)
            key_step = self.user.key_frame_step
            self.detection_handler.init_detector(camera_index, dimensions, backend, frame_start, key_step, "stream")

        # initialize the bridge from the detector to blender
        self.detection_handler.init_bridge()

        # add a timer property and start running
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        print(f"RUNNING {detection_type} DETECTION AS MODAL")
        return {'RUNNING_MODAL'}

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'POSE'}

    def modal(self, context, event):
        """ Run detection as modal operation, finish with 'Q', 'ESC' or 'RIGHT MOUSE'. """
        if event.type == "TIMER":
            running = self.detection_handler.detector.image_detection()
            if running:
                return {'PASS_THROUGH'}
            else:
                return self.cancel(context)

        if event.type in {'Q', 'ESC', 'RIGHT_MOUSE'} or self.user.detection_operator_running is False:
            return self.cancel(context)

        return {'PASS_THROUGH'}

    def cancel(self, context):
        """ Upon finishing detection clear the handlers. """
        bpy.context.scene.m_cgtinker_mediapipe.detection_operator_running = False # noqa
        del self.detection_handler
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        print("FINISHED DETECTION")
        return {'FINISHED'}
