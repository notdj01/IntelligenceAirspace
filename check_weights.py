import torch
import os

base_dir = r"d:\airspace_monitor\data_prepared"
models = ["airplane_lstm.pth", "pigeon_lstm.pth"]

for m in models:
    path = os.path.join(base_dir, m)
    if os.path.exists(path):
        try:
            ckpt = torch.load(path, map_location='cpu', weights_only=False)
            state_dict = ckpt['model_state_dict']
            nan_found = False
            for k, v in state_dict.items():
                if torch.isnan(v).any():
                    print(f"{m} - {k} has NaNs!")
                    nan_found = True
            if not nan_found:
                print(f"{m} is clean.")
            print(f"Norm: {ckpt.get('normalization')}")
        except Exception as e:
            print(f"Error loading {m}: {e}")
