import os
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt

class TrajectoryDataset(Dataset):
    def __init__(self, data_file, seq_length=10, pred_length=5):
        self.seq_length = seq_length
        self.pred_length = pred_length
        self.data = pd.read_csv(data_file)
        
        # We need groups of sequences for each obj_id
        self.sequences = []
        
        # Create sequences of deltas
        print(f"Loading data from {data_file}...")
        all_deltas = []
        max_samples = 50000
        for obj_id, group in self.data.groupby('obj_id'):
            coords = group[['lat', 'lon', 'alt']].values
            if len(coords) > 1:
                deltas = np.diff(coords, axis=0) # (N-1, 3)
                if len(deltas) >= (self.seq_length + self.pred_length):
                    for i in range(len(deltas) - self.seq_length - self.pred_length):
                        if len(self.sequences) >= max_samples:
                            break
                        seq = deltas[i:i+self.seq_length]
                        label = deltas[i+self.seq_length : i+self.seq_length+self.pred_length]
                        self.sequences.append((seq, label))
                        all_deltas.extend(seq)
            if len(self.sequences) >= max_samples:
                print(f"Reached max samples {max_samples} for {data_file}")
                break
                
        all_deltas = np.array(all_deltas)
        # Filter out NaNs and Infs before mean/std
        all_deltas = all_deltas[np.isfinite(all_deltas).all(axis=1)]
        
        if len(all_deltas) > 0:
            self.lat_mean, self.lon_mean, self.alt_mean = np.mean(all_deltas, axis=0)
            self.lat_std, self.lon_std, self.alt_std = np.std(all_deltas, axis=0)
        else:
            self.lat_mean, self.lon_mean, self.alt_mean = 0.0, 0.0, 0.0
            self.lat_std, self.lon_std, self.alt_std = 1.0, 1.0, 1.0
            
        self.lat_std = float(self.lat_std) if float(self.lat_std) > 0 else 1.0
        self.lon_std = float(self.lon_std) if float(self.lon_std) > 0 else 1.0
        self.alt_std = float(self.alt_std) if float(self.alt_std) > 0 else 1.0
        
        valid_sequences = []
        for i in range(len(self.sequences)):
            seq, label = self.sequences[i]
            if not (np.isfinite(seq).all() and np.isfinite(label).all()):
                continue
                
            seq_copy = np.copy(seq)
            label_copy = np.copy(label)
            
            seq_copy[:, 0] = (seq_copy[:, 0] - self.lat_mean) / self.lat_std
            seq_copy[:, 1] = (seq_copy[:, 1] - self.lon_mean) / self.lon_std
            seq_copy[:, 2] = (seq_copy[:, 2] - self.alt_mean) / self.alt_std
            
            label_copy[:, 0] = (label_copy[:, 0] - self.lat_mean) / self.lat_std
            label_copy[:, 1] = (label_copy[:, 1] - self.lon_mean) / self.lon_std
            label_copy[:, 2] = (label_copy[:, 2] - self.alt_mean) / self.alt_std
            
            # Clip outliers
            seq_copy = np.clip(seq_copy, -10.0, 10.0)
            label_copy = np.clip(label_copy, -10.0, 10.0)
            
            valid_sequences.append((seq_copy, label_copy))
            
        self.sequences = valid_sequences

    def __len__(self):
        return len(self.sequences)
        
    def __getitem__(self, idx):
        seq, label = self.sequences[idx]
        return torch.FloatTensor(seq), torch.FloatTensor(label)

class TrajectoryLSTM(nn.Module):
    def __init__(self, input_size=3, hidden_size=64, num_layers=2, output_size=3, pred_length=5):
        super(TrajectoryLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.pred_length = pred_length
        self.output_size = output_size
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size * pred_length)
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        # Use only the last hidden state
        out = self.fc(out[:, -1, :])
        return out.view(-1, self.pred_length, self.output_size)


def train_model(data_file, model_save_path, epochs=10, batch_size=32):
    print(f"Preparing dataset from {data_file}")
    dataset = TrajectoryDataset(data_file, seq_length=10, pred_length=5)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = TrajectoryLSTM().to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print(f"Starting training on {device}...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_idx, (inputs, targets) in enumerate(dataloader):
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {avg_loss:.4f}")
        
    print(f"Saving model to {model_save_path}")
    torch.save({
        'model_state_dict': model.state_dict(),
        'normalization': {
            'lat_mean': dataset.lat_mean,
            'lat_std': dataset.lat_std,
            'lon_mean': dataset.lon_mean,
            'lon_std': dataset.lon_std,
            'alt_mean': dataset.alt_mean,
            'alt_std': dataset.alt_std
        }
    }, model_save_path)
    print("Training complete.")

if __name__ == "__main__":
    base_dir = r"d:\airspace_monitor\data_prepared"
    
    # Train for pigeon (birds)
    pigeon_csv = os.path.join(base_dir, "pigeon_trajectories.csv")
    if os.path.exists(pigeon_csv):
        train_model(pigeon_csv, os.path.join(base_dir, "pigeon_lstm.pth"), epochs=5)
        
    # Train for trajair (airplanes)
    trajair_csv = os.path.join(base_dir, "trajair_trajectories.csv")
    if os.path.exists(trajair_csv):
        train_model(trajair_csv, os.path.join(base_dir, "airplane_lstm.pth"), epochs=5)
