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


class MiniMaxH3StitchAdvanced:
    """Advanced stitcher: includes film-grade temporal histogram CDF matching."""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "start_images": ("IMAGE",),
                "bridge_video": ("IMAGE",),
                "end_images": ("IMAGE",),
                "method": (["histogram", "linear_stats", "off"], {
                    "default": "histogram",
                    "tooltip": "histogram = Exact CDF curve matching (film quality). linear_stats = Fast mean/std ramp. off = Untouched."
                }),
                "strength": ("FLOAT", {
                    "default": 1.0, 
                    "min": 0.0, 
                    "max": 1.0, 
                    "step": 0.05,
                    "tooltip": "1.0 = Full tonal lock, 0.5 = 50% blend with raw bridge, 0.0 = Raw untouched bridge."
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("video",)
    FUNCTION = "stitch_advanced"
    CATEGORY = "DJBFilmz/H3"

    @staticmethod
    def _compute_cdf(frame_flat, bins=256):
        """Computes normalized Cumulative Distribution Function for (C, HW) tensor."""
        C = frame_flat.shape[0]
        device = frame_flat.device
        bin_indices = (frame_flat * (bins - 1)).long().clamp(0, bins - 1)
        hist = torch.zeros(C, bins, device=device, dtype=torch.float32)
        hist.scatter_add_(1, bin_indices, torch.ones_like(frame_flat))
        cdf = hist.cumsum(1)
        return cdf / cdf[:, -1:].clamp_min(1e-6)

    def stitch_advanced(self, start_images, bridge_video, end_images, method="histogram", strength=1.0):
        s_len = start_images.shape[0] if start_images is not None else 0
        b_len = bridge_video.shape[0] if bridge_video is not None else 0
        e_len = end_images.shape[0] if end_images is not None else 0

        if method != "off" and strength > 0.0 and b_len > 1 and s_len > 0 and e_len > 0:
            ref_start = start_images[-1:]  # Last frame of Video 1
            ref_end = end_images[0:1]      # First frame of Video 2
            B, H, W, C = bridge_video.shape
            device = bridge_video.device
            dtype = bridge_video.dtype

            if method == "histogram":
                # Extract reference flat tensors (C, HW)
                r1_flat = ref_start[0].permute(2, 0, 1).reshape(C, -1).to(device=device, dtype=torch.float32)
                r2_flat = ref_end[0].permute(2, 0, 1).reshape(C, -1).to(device=device, dtype=torch.float32)

                r1_cdf = self._compute_cdf(r1_flat, bins=256)
                r2_cdf = self._compute_cdf(r2_flat, bins=256)

                corrected_frames = []
                for i in range(B):
                    src = bridge_video[i].permute(2, 0, 1).to(device=device, dtype=torch.float32)
                    src_flat = src.reshape(C, -1)

                    # Compute current bridge frame's CDF
                    s_cdf = self._compute_cdf(src_flat, bins=256)

                    # Temporal blend of reference CDFs
                    alpha = i / max(1, B - 1)
                    target_cdf = (1.0 - alpha) * r1_cdf + alpha * r2_cdf

                    # Build LUT matching current frame CDF to target CDF
                    lut = torch.searchsorted(target_cdf, s_cdf).clamp_max_(255).float() / 255.0

                    # Map pixels using LUT
                    bin_idx = (src_flat * 255).long().clamp(0, 255)
                    matched = lut.gather(1, bin_idx).view(C, H, W)

                    if strength < 1.0:
                        matched = torch.lerp(src, matched, strength)

                    corrected_frames.append(matched.permute(1, 2, 0).clamp_(0.0, 1.0).to(dtype))

                bridge_video = torch.stack(corrected_frames, dim=0)
                print(f"[MiniMax H3 Stitch Advanced] Applied Temporal Histogram Matching across {B} frames (strength: {strength}).")

            elif method == "linear_stats":
                mean_start = ref_start.mean(dim=(1, 2), keepdim=True).to(device)
                std_start = ref_start.std(dim=(1, 2), keepdim=True).to(device) + 1e-6

                mean_end = ref_end.mean(dim=(1, 2), keepdim=True).to(device)
                std_end = ref_end.std(dim=(1, 2), keepdim=True).to(device) + 1e-6

                b_mean = bridge_video.mean(dim=(1, 2), keepdim=True)
                b_std = bridge_video.std(dim=(1, 2), keepdim=True) + 1e-6

                norm_bridge = (bridge_video - b_mean) / b_std
                t = torch.linspace(0.0, 1.0, steps=B, device=device).view(B, 1, 1, 1).expand(-1, -1, -1, C)

                target_mean = (1.0 - t) * mean_start + t * mean_end
                target_std = (1.0 - t) * std_start + t * std_end

                corrected = torch.clamp(norm_bridge * target_std + target_mean, 0.0, 1.0)
                bridge_video = (1.0 - strength) * bridge_video + strength * corrected
                print(f"[MiniMax H3 Stitch Advanced] Applied Linear Stats Matching across {B} frames (strength: {strength}).")

        # Assemble the 3 pieces
        pieces = [p for p in [start_images, bridge_video, end_images] if p is not None and p.shape[0] > 0]
        full_video = torch.cat(pieces, dim=0)

        print(f"[MiniMax H3 Stitch Advanced] Assembled: {s_len} (start) + {b_len} (bridge) + {e_len} (end) = {full_video.shape[0]} total frames.")
        return (full_video,)


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3": MiniMaxH3,
    "MiniMaxH3Stitch": MiniMaxH3Stitch,
    "MiniMaxH3StitchAdvanced": MiniMaxH3StitchAdvanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3": " MiniMax H3 Join",
    "MiniMaxH3Stitch": " MiniMax H3 Stitch",
    "MiniMaxH3StitchAdvanced": "MiniMax H3 Stitch Advanced",
}