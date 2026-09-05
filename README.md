# ComfyUI MiniMax H3 Clip Joiner

## UPDATE

Added `MiniMax H3 Stitch Advanced`. This node's primary function is to color match the start and end images. You can use this in lieu of the MiniMax H3 Stitch node if you're having color accuracy issues.

<img width="300" height="auto" alt="H3_Stitch_Advanced" src="https://github.com/user-attachments/assets/aba482cd-22a5-4bc4-b858-794c5d4458e9" />

---

I created a very simple joiner to join two clips together using MiniMax H3 Image to Video workflow.



Shout-out to Stuttlepress for giving me the idea with his ComfyUI-Wan-VACE-Prep Nodes.

<img width="auto" height="300" alt="H3_Join" src="https://github.com/user-attachments/assets/ec9fd131-a0bb-4ace-8983-47203ecbd34a" />
<img width="300" height="auto" alt="H3_Stitch" src="https://github.com/user-attachments/assets/cc619a94-2f7f-4495-933a-d45ed2db7aa6" />

This node is extremely simple, as I “vibe coded” it as if I were a 5-year-old.

---

## Explanation

| Node Output | Where to Connect It |
| :--- | :--- |
| **Video_1** | Your start video |
| **Video_2** | Your end video |
| **First_frame** | Plug this into `first_frame` on H3 Image to Video Conditioning node |
| **Last_frame** | Plug this into `first_frame` on H3 Image to Video Conditioning node |
| **Start_images** | Plug this into the `start_images` on the MiniMax H3 Stitch node |
| **End_images** | Plug this into the `end_images` on the MiniMax H3 Stitch node |

---

## Settings & Controls

* **Bridge_frames:** Bridge_frames is essentially how many frames you want to create. The math is calculated inside the node, so you don’t need to worry about it. Just click through, and it works.

* **Keep_original_duration:** (this is my favorite) this will basically erase the frames from your Start and End video, making it so that you have the exact duration that those two videos equal. 
  
  > **Reasoning:** As a filmmaker, I want the video to stay the exact length to keep the performance as intended. 
  > 
  > *Note: Select false on this if you prefer to add NEW frames.*

* **Replace_frames:** this is similar to keep original in that it deletes frames from the start and end video. However, it does not do the precise calculation needed to keep the original duration. 
  
  > *Note: Only use when keep_original_duration is set to FALSE.*

---

## Workflow Example Image
<img width="1823" height="854" alt="H3_Join_WF" src="https://github.com/user-attachments/assets/7437b963-1369-4e0e-8da7-3db9609962e6" />

---

## Installation

```bash
cd ComfyUI/custom_nodes/
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
