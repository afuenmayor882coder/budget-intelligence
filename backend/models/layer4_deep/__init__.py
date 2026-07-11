"""Layer 4: Deep learning forecasting models (no PyTorch dependency).

Models:
- lstm_gru  : Echo State Networks — proper recurrent networks trainable with ridge regression
- nbeats    : N-BEATS with greedy block stacking (trend + seasonality + generic)
- temporal_fusion : Simplified TFT with multi-horizon MLP + variable selection
- deepar    : DeepAR proxy — probabilistic forecasts via bootstrap ensemble
"""
