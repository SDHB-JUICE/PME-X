"""
Telegram Alert Service
Send alerts to Telegram chat
"""
import requests
import logging
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_alert(message, parse_mode="HTML", disable_web_page_preview=True):
    """Send alert to Telegram chat
    
    Args:
        message (str): Message to send
        parse_mode (str): Parse mode (HTML, Markdown)
        disable_web_page_preview (bool): Whether to disable web page preview
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    try:
        # Get Telegram bot token and chat ID from config
        bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
        chat_id = current_app.config.get('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            logger.warning("Telegram bot token or chat ID not set")
            return False
        
        # Send message
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_page_preview
            },
            timeout=10
        )
        
        # Check response
        if response.status_code != 200:
            logger.error(f"Failed to send Telegram alert: {response.text}")
            return False
        
        logger.info(f"Telegram alert sent: {message[:50]}...")
        return True
        
    except Exception as e:
        logger.error(f"Error sending Telegram alert: {str(e)}")
        return False

def send_trade_alert(trade):
    """Send alert for a trade
    
    Args:
        trade (Trade): Trade model
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    try:
        # Format message
        if trade.status == "completed":
            emoji = "✅" if trade.net_profit > 0 else "⚠️"
            message = f"{emoji} <b>{trade.strategy_type.title()}</b> trade on <b>{trade.chain}</b>\n\n"
            message += f"Amount: ${trade.amount:.2f}\n"
            message += f"Profit: ${trade.profit:.2f}\n"
            message += f"Gas cost: ${trade.gas_cost:.2f}\n"
            message += f"<b>Net profit: ${trade.net_profit:.2f}</b>\n\n"
            
            if trade.tx_hash:
                message += f"<a href='https://etherscan.io/tx/{trade.tx_hash}'>View transaction</a>"
        else:
            message = f"❌ <b>{trade.strategy_type.title()}</b> trade failed on <b>{trade.chain}</b>\n\n"
            
            if trade.details and 'error' in trade.details:
                message += f"Error: {trade.details['error']}\n\n"
            
        return send_alert(message)
        
    except Exception as e:
        logger.error(f"Error sending trade alert: {str(e)}")
        return False

def send_yield_farm_alert(farm, action):
    """Send alert for a yield farm
    
    Args:
        farm (YieldFarm): YieldFarm model
        action (str): Action (deposit, harvest, withdraw)
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    try:
        # Format message
        if action == "deposit":
            message = f"🌱 <b>New Yield Farm</b> on <b>{farm.chain}</b>\n\n"
            message += f"Protocol: {farm.protocol}\n"
            message += f"Pool: {farm.pool_name}\n"
            message += f"Amount: ${farm.deposit_amount:.2f}\n"
            message += f"APY: {farm.apy:.2f}%\n\n"
            
            if farm.deposit_tx:
                message += f"<a href='https://etherscan.io/tx/{farm.deposit_tx}'>View transaction</a>"
                
        elif action == "harvest":
            message = f"🌾 <b>Yield Farm Harvested</b> on <b>{farm.chain}</b>\n\n"
            message += f"Protocol: {farm.protocol}\n"
            message += f"Pool: {farm.pool_name}\n"
            message += f"Original deposit: ${farm.deposit_amount:.2f}\n"
            message += f"Current value: ${farm.current_value:.2f}\n"
            message += f"Profit: ${farm.current_value - farm.deposit_amount:.2f}\n\n"
            
            if farm.last_harvest_tx:
                message += f"<a href='https://etherscan.io/tx/{farm.last_harvest_tx}'>View transaction</a>"
                
        elif action == "withdraw":
            message = f"💰 <b>Yield Farm Withdrawn</b> on <b>{farm.chain}</b>\n\n"
            message += f"Protocol: {farm.protocol}\n"
            message += f"Pool: {farm.pool_name}\n"
            message += f"Original deposit: ${farm.deposit_amount:.2f}\n"
            message += f"Final value: ${farm.current_value:.2f}\n"
            message += f"Profit: ${farm.current_value - farm.deposit_amount:.2f}\n\n"
            
            if farm.withdraw_tx:
                message += f"<a href='https://etherscan.io/tx/{farm.withdraw_tx}'>View transaction</a>"
        
        return send_alert(message)
        
    except Exception as e:
        logger.error(f"Error sending yield farm alert: {str(e)}")
        return False

def send_token_alert(token):
    """Send alert for a deployed token
    
    Args:
        token (DeployedToken): DeployedToken model
        
    Returns:
        bool: True if alert was sent successfully, False otherwise
    """
    try:
        # Format message
        message = f"🪙 <b>New Token Deployed</b> on <b>{token.chain}</b>\n\n"
        message += f"Name: {token.name}\n"
        message += f"Symbol: {token.symbol}\n"
        message += f"Total supply: {token.total_supply:,.0f}\n"
        message += f"Address: <code>{token.address}</code>\n\n"
        
        if token.deploy_tx:
            message += f"<a href='https://etherscan.io/tx/{token.deploy_tx}'>View transaction</a>"
        
        return send_alert(message)
        
    except Exception as e:
        logger.error(f"Error sending token alert: {str(e)}")
        return False