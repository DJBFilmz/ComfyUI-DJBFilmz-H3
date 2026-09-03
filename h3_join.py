import torch


class MiniMaxH3:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_1": ("IMAGE",),
                "video_2": ("IMAGE",),
                "bridge_frames": ("INT", {
                    "default": 56, 
                    "min": 22, 
                    "max": 362, 
                    "step": 17,
                    "tooltip": "Transition size (17k+5). 22=0.9s, 39=1.6s, 56=2.3s, 124=5.1s."
                }),
                "keep_original_duration": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "TRUE = Replaces frames so total video length NEVER increases. FALSE = Adds extra frames."
                }),
                "replace_frames": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 120, 
                    "step": 1,
                    "tooltip": "Only used when keep_original_duration is False."
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "INT", "INT", "INT", "IMAGE", "IMAGE")
    RETURN_NAMES = ("first_frame", "last_frame", "width", "height", "length", "start_images", "end_images")
    FUNCTION = "join"
    CATEGORY = "DJBFilmz/H3"

    def join(self, video_1, video_2, bridge_frames, keep_original_duration, replace_frames):
        height = video_1.shape[1]
        width = video_1.shape[2]

        if video_2.shape[1] != height or video_2.shape[2] != width:
            raise ValueError(f"Sizes don't match! Video 1 is {width}x{height}, Video 2 is {video_2.shape[2]}x{video_2.shape[1]}")

        # 1. AUTO-FIX: Ensure Width and Height are divisible by 32 for H3
        new_height = (height // 32) * 32
        new_width = (width // 32) * 32

        if new_height != height or new_width != width:
            top = (height - new_height) // 2
            left = (width - new_width) // 2
            video_1 = video_1[:, top : top + new_height, left : left + new_width, :]
            video_2 = video_2[:, top : top + new_height, left : left + new_width, :]
            print(f"[MiniMax H3 Join] Auto-cropped from {width}x{height} to {new_width}x{new_height} (multiples of 32 for H3).")
            height, width = new_height, new_width

        # 2. Snap bridge_frames to H3's 17k + 5 rule
        k = max(1, round((bridge_frames - 5) / 17))
        valid_length = int(17 * k + 5)

        v1_len = video_1.shape[0]
        v2_len = video_2.shape[0]

        # 3. Slicing logic
        if keep_original_duration:
            # Erase valid_length frames total across both videos to keep total length constant
            trim_1 = valid_length // 2
            trim_2 = valid_length - trim_1

            if v1_len <= trim_1:
                raise ValueError(f"Video 1 only has {v1_len} frames, but needs more than {trim_1} to replace {valid_length} frames.")
            if v2_len <= trim_2:
                raise ValueError(f"Video 2 only has {v2_len} frames, but needs more than {trim_2} to replace {valid_length} frames.")

            # Keep video 1 up to the cut, and pick the first frame for H3
            start_images = video_1[: v1_len - trim_1]
            first_frame = video_1[v1_len - trim_1 : v1_len - trim_1 + 1]

            # Pick the landing frame for H3 in video 2, and keep the rest
            last_frame = video_2[trim_2 - 1 : trim_2]
            end_images = video_2[trim_2 :]

            print(f"[MiniMax H3 Join] ZERO frames added! Replaced {trim_1} frames from V1 and {trim_2} frames from V2 with a {valid_length}-frame bridge.")
        else:
            # Classic mode: Adds bridge frames between videos
            min_needed = replace_frames + 1
            if v1_len < min_needed or v2_len < min_needed:
                raise ValueError(f"Videos must have at least {min_needed} frames.")

            cut_v1 = replace_frames + 1
            start_images = video_1[:-cut_v1]
            first_frame = video_1[-cut_v1 : -replace_frames if replace_frames > 0 else None]

            cut_v2 = replace_frames
            last_frame = video_2[cut_v2 : cut_v2 + 1]
            end_images = video_2[cut_v2 + 1 :]

        return (first_frame, last_frame, width, height, valid_length, start_images, end_images)


class MiniMaxH3Stitch:
    """Glues the 3 pieces back together on your local GPU."""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "start_images": ("IMAGE",),
                "end_images": ("IMAGE",),
                "bridge_video": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("video",)
    FUNCTION = "stitch"
    CATEGORY = "DJBFilmz/H3"

    def stitch(self, start_images, bridge_video, end_images):
        pieces = [p for p in [start_images, bridge_video, end_images] if p is not None and p.shape[0] > 0]
        full_video = torch.cat(pieces, dim=0)
        return (full_video,)


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3": MiniMaxH3,
    "MiniMaxH3Stitch": MiniMaxH3Stitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3": " MiniMax H3 Join",
    "MiniMaxH3Stitch": " MiniMax H3 Stitch",
}