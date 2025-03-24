"""
AI Predictor Service
Uses TensorFlow to predict optimal trading opportunities
"""
import os
import time
import json
import logging
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from app import db
from app.models.trade import Trade
from app.models.wallet import ChainInfo
from app.utils.web3_helper import get_token_price

# Optional TensorFlow import, we'll handle the case if it's not installed
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIPredictorService:
    """Service for predicting optimal trading opportunities using AI/ML"""
    
    def __init__(self):
        """Initialize AI predictor service"""
        self.tf_available = TF_AVAILABLE
        self.model = None
        self.scaler = None
        
        # Check if AI prediction is enabled
        self.enabled = os.environ.get('ENABLE_AI_PREDICTIONS', 'false').lower() == 'true'
        
        if self.enabled and not self.tf_available:
            logger.warning("AI predictions are enabled, but TensorFlow is not installed")
            self.enabled = False
        
        logger.info(f"Initialized AIPredictorService (enabled: {self.enabled}, TensorFlow available: {self.tf_available})")
    
    def load_model(self, model_path=None):
        """Load the TensorFlow model
        
        Args:
            model_path (str, optional): Path to saved model
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        if not self.tf_available:
            logger.error("Cannot load model: TensorFlow is not installed")
            return False
        
        try:
            # If model_path is provided, load the model
            if model_path and os.path.exists(model_path):
                self.model = tf.keras.models.load_model(model_path)
                logger.info(f"Loaded model from {model_path}")
                return True
            else:
                # Create a simple model for demonstration purposes
                logger.info("Creating demonstration model")
                self.model = tf.keras.Sequential([
                    tf.keras.layers.Dense(128, activation='relu', input_shape=(10,)),
                    tf.keras.layers.Dropout(0.2),
                    tf.keras.layers.Dense(64, activation='relu'),
                    tf.keras.layers.Dropout(0.1),
                    tf.keras.layers.Dense(32, activation='relu'),
                    tf.keras.layers.Dense(1, activation='sigmoid')
                ])
                
                self.model.compile(optimizer='adam',
                                 loss='binary_crossentropy',
                                 metrics=['accuracy'])
                
                return True
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def prepare_historical_data(self):
        """Prepare historical data for model training/prediction
        
        Returns:
            pandas.DataFrame: Processed data
        """
        try:
            # Get historical trade data
            trades = Trade.query.order_by(Trade.created_at.asc()).all()
            
            if not trades:
                logger.warning("No historical trade data found")
                return None
            
            # Convert to DataFrame
            data = []
            for trade in trades:
                try:
                    # Extract relevant features
                    row = {
                        'timestamp': trade.created_at,
                        'strategy_type': trade.strategy_type,
                        'chain': trade.chain,
                        'amount': trade.amount,
                        'profit': trade.profit,
                        'gas_cost': trade.gas_cost,
                        'net_profit': trade.net_profit,
                        'execution_time': trade.execution_time or 0,
                        'success': 1 if trade.status == 'completed' and trade.net_profit > 0 else 0
                    }
                    
                    # Add details if available
                    if trade.details:
                        if isinstance(trade.details, str):
                            details = json.loads(trade.details)
                        else:
                            details = trade.details
                        
                        # Add relevant details as features
                        if trade.strategy_type == 'flash_loan':
                            row['token'] = details.get('token', 'unknown')
                            row['dex1'] = details.get('dex1', 'unknown')
                            row['dex2'] = details.get('dex2', 'unknown')
                        elif trade.strategy_type == 'cross_chain':
                            row['token'] = details.get('token', 'unknown')
                            row['source_chain'] = details.get('source_chain', 'unknown')
                            row['target_chain'] = details.get('target_chain', 'unknown')
                    
                    data.append(row)
                except Exception as inner_e:
                    logger.error(f"Error processing trade {trade.id}: {str(inner_e)}")
                    continue
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            if df.empty:
                logger.warning("No valid trade data processed")
                return None
            
            # Add time-based features
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            
            # Add profitability ratio
            df['profit_ratio'] = df['net_profit'] / df['amount']
            
            # Handle categorical variables
            df = pd.get_dummies(df, columns=['strategy_type', 'chain'])
            
            # Remove non-numerical columns
            df = df.drop(['timestamp'], axis=1, errors='ignore')
            
            # Remove rows with NaN values
            df = df.dropna()
            
            return df
            
        except Exception as e:
            logger.error(f"Error preparing historical data: {str(e)}")
            return None
    
    def train_model(self):
        """Train the model on historical data
        
        Returns:
            bool: True if training successful, False otherwise
        """
        if not self.tf_available:
            logger.error("Cannot train model: TensorFlow is not installed")
            return False
        
        if not self.model:
            if not self.load_model():
                return False
        
        try:
            # Prepare data
            data = self.prepare_historical_data()
            
            if data is None or len(data) < 10:
                logger.error("Insufficient data for training")
                return False
            
            # Split features and target
            X = data.drop(['success', 'net_profit', 'profit'], axis=1, errors='ignore')
            y = data['success']
            
            # Scale features
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            self.scaler = scaler
            
            # Split into train/test
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
            
            # Train model
            self.model.fit(X_train, y_train, epochs=50, batch_size=32, validation_data=(X_test, y_test), verbose=0)
            
            # Evaluate
            _, accuracy = self.model.evaluate(X_test, y_test, verbose=0)
            logger.info(f"Model training complete. Accuracy: {accuracy:.4f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False
    
    def predict_best_strategy(self, chains=None, strategies=None, amount=10000):
        """Predict the best trading strategy
        
        Args:
            chains (list, optional): List of chains to consider
            strategies (list, optional): List of strategies to consider
            amount (float, optional): Amount to trade
            
        Returns:
            dict: Predicted best strategy
        """
        start_time = time.time()
        
        if not self.enabled:
            return {
                'success': False,
                'error': "AI predictions are not enabled",
                'execution_time': time.time() - start_time
            }
        
        if not self.tf_available:
            return {
                'success': False,
                'error': "TensorFlow is not installed",
                'execution_time': time.time() - start_time
            }
        
        try:
            # Load model if not already loaded
            if not self.model and not self.load_model():
                return {
                    'success': False,
                    'error': "Failed to load model",
                    'execution_time': time.time() - start_time
                }
            
            # Get available chains
            if not chains:
                chain_infos = ChainInfo.query.filter_by(status='active').all()
                chains = [chain.name for chain in chain_infos]
            
            # Get available strategies
            if not strategies:
                strategies = ['flash_loan', 'multi_hop', 'cross_chain', 'yield_farming']
            
            # Prepare candidate strategies
            candidates = []
            
            # Generate candidates for each strategy and chain combination
            for strategy in strategies:
                for chain in chains:
                    # Skip cross_chain if only one chain
                    if strategy == 'cross_chain' and len(chains) < 2:
                        continue
                    
                    # For cross_chain, generate pairs of chains
                    if strategy == 'cross_chain':
                        for target_chain in chains:
                            if target_chain != chain:
                                candidates.append({
                                    'strategy_type': strategy,
                                    'chain': f"{chain}->{target_chain}",
                                    'source_chain': chain,
                                    'target_chain': target_chain,
                                    'amount': amount
                                })
                    else:
                        candidates.append({
                            'strategy_type': strategy,
                            'chain': chain,
                            'amount': amount
                        })
            
            # If we have no candidates, return error
            if not candidates:
                return {
                    'success': False,
                    'error': "No valid strategy candidates found",
                    'execution_time': time.time() - start_time
                }
            
            # Enhanced with market conditions and other features
            enhanced_candidates = []
            
            for candidate in candidates:
                chain = candidate['chain'].split('->')[0] if '->' in candidate['chain'] else candidate['chain']
                
                # Get chain info
                chain_info = ChainInfo.query.filter_by(name=chain).first()
                
                if not chain_info:
                    continue
                
                enhanced = candidate.copy()
                
                # Add gas price
                enhanced['gas_price'] = chain_info.avg_gas_price or 50  # Default to 50 gwei
                
                # Add time features
                now = datetime.utcnow()
                enhanced['hour'] = now.hour
                enhanced['day_of_week'] = now.weekday()
                
                # For flash loans, add token prices
                if candidate['strategy_type'] == 'flash_loan':
                    enhanced['token'] = 'USDC'  # Default to USDC
                    enhanced['dex1'] = 'uniswap'
                    enhanced['dex2'] = 'sushiswap'
                
                enhanced_candidates.append(enhanced)
            
            # Convert candidates to DataFrame
            candidates_df = pd.DataFrame(enhanced_candidates)
            
            # Prepare for model prediction
            # This would normally require the exact same preprocessing as training data
            # For demo purposes, we'll simulate this
            
            # Add dummy variables for categorical features
            candidates_df = pd.get_dummies(candidates_df, columns=['strategy_type', 'chain'])
            
            # Align with training data columns (simplified for demo)
            # In a real implementation, you'd need to make sure all columns match exactly
            
            # Make prediction
            if len(candidates_df) == 0:
                return {
                    'success': False,
                    'error': "No valid candidates after preprocessing",
                    'execution_time': time.time() - start_time
                }
            
            # Simulate predictions for demo
            # In a real implementation, you'd use:
            # predictions = self.model.predict(candidates_df)
            
            # Instead, we'll generate random predictions
            predictions = np.random.rand(len(candidates_df))
            
            # Get best strategy
            best_idx = np.argmax(predictions)
            best_candidate = enhanced_candidates[best_idx]
            confidence = float(predictions[best_idx])
            
            # Add prediction info
            result = {
                'success': True,
                'strategy': best_candidate['strategy_type'],
                'chain': best_candidate['chain'],
                'amount': best_candidate['amount'],
                'confidence': confidence,
                'execution_time': time.time() - start_time
            }
            
            # Add strategy-specific details
            if best_candidate['strategy_type'] == 'flash_loan':
                result['token'] = 'USDC'
                result['dex1'] = 'uniswap'
                result['dex2'] = 'sushiswap'
                result['expected_profit'] = best_candidate['amount'] * 0.015  # 1.5% profit estimate
            elif best_candidate['strategy_type'] == 'cross_chain':
                result['source_chain'] = best_candidate['source_chain']
                result['target_chain'] = best_candidate['target_chain']
                result['token'] = 'USDC'
                result['expected_profit'] = best_candidate['amount'] * 0.01  # 1% profit estimate
            elif best_candidate['strategy_type'] == 'multi_hop':
                result['expected_profit'] = best_candidate['amount'] * 0.02  # 2% profit estimate
            elif best_candidate['strategy_type'] == 'yield_farming':
                result['protocol'] = 'yearn'
                result['pool'] = 'usdc'
                result['apy'] = 8.5  # 8.5% APY estimate
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting best strategy: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def predict_gas_prices(self, chain):
        """Predict gas prices for the next 24 hours
        
        Args:
            chain (str): Chain name
            
        Returns:
            dict: Predicted gas prices
        """
        start_time = time.time()
        
        if not self.enabled:
            return {
                'success': False,
                'error': "AI predictions are not enabled",
                'execution_time': time.time() - start_time
            }
        
        try:
            # Get chain info
            chain_info = ChainInfo.query.filter_by(name=chain).first()
            if not chain_info:
                return {
                    'success': False,
                    'error': f"Chain {chain} not found",
                    'execution_time': time.time() - start_time
                }
            
            # Get current gas price
            current_gas = chain_info.avg_gas_price or 50  # Default to 50 gwei
            
            # Generate predictions for the next 24 hours
            hours = list(range(24))
            
            # In a real implementation, these would be model predictions
            # For demo, we'll simulate with a simple pattern
            gas_predictions = []
            
            for hour in hours:
                # Base prediction on current price with some hourly variation
                # This is a very simplified model for demonstration
                now = datetime.utcnow()
                future_hour = (now.hour + hour) % 24
                
                # Gas tends to be higher during US business hours (14-22 UTC)
                hour_factor = 1.2 if 14 <= future_hour <= 22 else 0.9
                
                # Weekend factor (gas tends to be lower on weekends)
                future_day = (now.weekday() + (now.hour + hour) // 24) % 7
                weekend_factor = 0.8 if future_day >= 5 else 1.0  # 5, 6 = weekend
                
                # Calculate predicted gas price
                predicted_gas = current_gas * hour_factor * weekend_factor
                
                # Add some random noise
                noise = np.random.normal(0, 0.1)  # 10% standard deviation
                predicted_gas *= (1 + noise)
                
                # Ensure gas price is reasonable
                predicted_gas = max(5, min(500, predicted_gas))
                
                gas_predictions.append({
                    'hour': hour,
                    'timestamp': (now + timedelta(hours=hour)).isoformat(),
                    'gas_price': round(predicted_gas, 1)
                })
            
            return {
                'success': True,
                'chain': chain,
                'current_gas': current_gas,
                'predictions': gas_predictions,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error predicting gas prices: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def get_optimal_trade_time(self, chain, strategy_type, amount, time_window=24):
        """Get the optimal time to execute a trade within a given time window
        
        Args:
            chain (str): Chain name
            strategy_type (str): Strategy type
            amount (float): Amount to trade
            time_window (int): Time window in hours
            
        Returns:
            dict: Optimal trade time information
        """
        start_time = time.time()
        
        if not self.enabled:
            return {
                'success': False,
                'error': "AI predictions are not enabled",
                'execution_time': time.time() - start_time
            }
        
        try:
            # Get gas price predictions
            gas_prediction = self.predict_gas_prices(chain)
            
            if not gas_prediction['success']:
                return gas_prediction
            
            # Calculate expected profit at each hour
            trade_predictions = []
            
            for hour_data in gas_prediction['predictions'][:time_window]:
                hour = hour_data['hour']
                gas_price = hour_data['gas_price']
                timestamp = hour_data['timestamp']
                
                # Estimate gas cost
                # These are simplified estimates for demonstration
                if strategy_type == 'flash_loan':
                    gas_limit = 300000
                elif strategy_type == 'multi_hop':
                    gas_limit = 250000
                elif strategy_type == 'cross_chain':
                    gas_limit = 200000
                else:
                    gas_limit = 150000
                
                # Convert gas price from gwei to ether
                gas_price_ether = gas_price * 1e-9
                
                # Calculate gas cost in ether
                gas_cost_ether = gas_limit * gas_price_ether
                
                # Get ether price in USD (simplified)
                eth_price = 3000  # Placeholder price
                
                # Calculate gas cost in USD
                gas_cost_usd = gas_cost_ether * eth_price
                
                # Estimate profit based on strategy
                if strategy_type == 'flash_loan':
                    profit_estimate = amount * 0.015  # 1.5% profit
                elif strategy_type == 'multi_hop':
                    profit_estimate = amount * 0.02  # 2% profit
                elif strategy_type == 'cross_chain':
                    profit_estimate = amount * 0.01  # 1% profit
                else:
                    profit_estimate = amount * 0.005  # 0.5% profit
                
                # Calculate net profit
                net_profit = profit_estimate - gas_cost_usd
                
                # Calculate efficiency ratio (profit per gas)
                efficiency = net_profit / gas_cost_usd if gas_cost_usd > 0 else 0
                
                trade_predictions.append({
                    'hour': hour,
                    'timestamp': timestamp,
                    'gas_price': gas_price,
                    'gas_cost_usd': gas_cost_usd,
                    'profit_estimate': profit_estimate,
                    'net_profit': net_profit,
                    'efficiency': efficiency
                })
            
            # Find optimal time (highest net profit)
            optimal_time = max(trade_predictions, key=lambda x: x['net_profit'])
            
            # Find most efficient time (highest profit per gas)
            most_efficient_time = max(trade_predictions, key=lambda x: x['efficiency'])
            
            return {
                'success': True,
                'chain': chain,
                'strategy_type': strategy_type,
                'amount': amount,
                'optimal_time': optimal_time,
                'most_efficient_time': most_efficient_time,
                'predictions': trade_predictions,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error finding optimal trade time: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }