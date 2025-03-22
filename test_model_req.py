import numpy as np

# Example input data (replace with actual input values)
input_data_dict = {
    "input_ids": np.random.randint(0, 1022, size=(1, 128), dtype=np.int64),  # Random token IDs
    "attention_mask": np.ones((1, 128), dtype=np.float32)  # All ones (valid tokens)
}

# Construct ort_inputs properly
ort_inputs = {
    "input_ids": np.array(input_data_dict["input_ids"], dtype=np.int64),  # Ensure int64 dtype
    "attention_mask": np.array(input_data_dict["attention_mask"], dtype=np.float32)  # Ensure float32 dtype
}

# Print for verification
print("ORT Inputs:", ort_inputs)