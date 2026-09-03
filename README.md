# ComfyUI MiniMax H3 Clip Joiner

I created a very simple joiner to join two clips together using Minimax H3 Image to Video workflow.

Shout out to Stuttlepress for giving me the idea with his ComfyUI-Wan-VACE-Prep Nodes.

This node is extremely simple as I “vibe coded” it as if I were a 5-year-old.

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

* **Bridge_frames:** Bridge_frames is essentially how many frames you want to create. The math is calculated inside the node so you don’t need to worry about it. Just click through and it works.

* **Keep_original_duration:** (this is my favorite) this will basically erase the frames from your Start and End video making it so that your have the exact duration that those two video equal. 
  
  > **Reasoning:** as a filmmaker, I want the video to stay the exact length to keep the performance as intended. 
  > 
  > *Note: Select false on this if you prefer to add NEW frames.*

* **Replace_frames:** this is similar to keep original in that it deletes frames form the start and end video. However, it does not do the precise calculation needed to keep the original duration. 
  
  > *Note: Only use when keep_original_duration is set to FALSE.*

---

## Installation

```bash
cd ComfyUI/custom_nodes/
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)