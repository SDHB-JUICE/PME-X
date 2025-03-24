"""
Auto Harvest Service
Automatically harvests rewards from yield farming positions
"""
import time
import threading
import logging
from datetime import datetime, timedelta
from app import db
from app.models.trade import YieldFarm
from app.models.user import User, Settings
from app.services.yield_farming import YieldFarmingService
from app.services.telegram_alert import send_alert

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoHarvestService:
    """Service for automatically harvesting yield farming rewards"""
    
    def __init__(self):
        """Initialize auto harvest service"""
        self.running = False
        self.thread = None
        logger.info("Initialized AutoHarvestService")
    
    def start(self):
        """Start the auto harvest service"""
        if self.running:
            logger.warning("Auto harvest service already running")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._run_service)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Auto harvest service started")
        return True
    
    def stop(self):
        """Stop the auto harvest service"""
        if not self.running:
            logger.warning("Auto harvest service not running")
            return False
        
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("Auto harvest service stopped")
        return True
    
    def _run_service(self):
        """Run the service loop"""
        while self.running:
            try:
                # Check if auto-harvest is enabled globally
                auto_harvest_enabled = Settings.get('auto_harvest_enabled', 'true') == 'true'
                if not auto_harvest_enabled:
                    logger.info("Auto harvest is disabled globally")
                    time.sleep(3600)  # Sleep for 1 hour before checking again
                    continue
                
                # Get farms that need harvesting
                self._process_farms()
                
                # Sleep for the check interval
                check_interval = int(Settings.get('auto_harvest_interval', '3600'))  # Default: 1 hour
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in auto harvest service: {str(e)}")
                time.sleep(300)  # Sleep for 5 minutes before retrying
    
    def _process_farms(self):
        """Process farms that need harvesting"""
        try:
            # Get the threshold from settings
            harvest_threshold_hours = int(Settings.get('harvest_threshold_hours', '24'))
            
            # Find farms that need harvesting
            threshold_time = datetime.utcnow() - timedelta(hours=harvest_threshold_hours)
            
            # Find farms that haven't been harvested for the threshold time
            farms_to_harvest = YieldFarm.query.filter(
                (YieldFarm.status == 'active') &
                (
                    (YieldFarm.last_harvest == None) |
                    (YieldFarm.last_harvest < threshold_time)
                )
            ).all()
            
            logger.info(f"Found {len(farms_to_harvest)} farms to harvest")
            
            # Process each farm
            for farm in farms_to_harvest:
                self._harvest_farm(farm)
                
                # Sleep briefly between harvests to avoid overloading
                time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error processing farms: {str(e)}")
    
    def _harvest_farm(self, farm):
        """Harvest a specific farm
        
        Args:
            farm (YieldFarm): Farm to harvest
        """
        try:
            logger.info(f"Harvesting farm {farm.id} on {farm.chain}")
            
            # Get private key from environment (in production, this would be securely stored)
            # This is just a placeholder - in a real service, you'd have a key management system
            private_key = f"0xprivate_key_for_{farm.chain}"
            
            # Initialize yield farming service
            yield_service = YieldFarmingService(farm.chain, private_key)
            
            # Execute harvest
            result = yield_service.execute_harvest(farm.id)
            
            if result['success']:
                logger.info(f"Successfully harvested farm {farm.id} with profit ${result['profit']:.2f}")
            else:
                logger.error(f"Failed to harvest farm {farm.id}: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"Error harvesting farm {farm.id}: {str(e)}")
    
    def manually_harvest_all(self):
        """Manually trigger harvesting of all eligible farms
        
        Returns:
            dict: Result of the operation
        """
        start_time = time.time()
        
        try:
            # Find active farms
            farms_to_harvest = YieldFarm.query.filter_by(status='active').all()
            
            if not farms_to_harvest:
                return {
                    'success': True,
                    'message': 'No active farms found to harvest',
                    'harvested': 0,
                    'execution_time': time.time() - start_time
                }
            
            # Track results
            results = {
                'total': len(farms_to_harvest),
                'successful': 0,
                'failed': 0,
                'details': []
            }
            
            # Process each farm
            for farm in farms_to_harvest:
                try:
                    # Get private key (placeholder)
                    private_key = f"0xprivate_key_for_{farm.chain}"
                    
                    # Initialize yield farming service
                    yield_service = YieldFarmingService(farm.chain, private_key)
                    
                    # Execute harvest
                    result = yield_service.execute_harvest(farm.id)
                    
                    # Track result
                    if result['success']:
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                    
                    results['details'].append({
                        'farm_id': farm.id,
                        'chain': farm.chain,
                        'protocol': farm.protocol,
                        'pool': farm.pool_name,
                        'success': result['success'],
                        'profit': result.get('profit', 0) if result['success'] else 0,
                        'error': result.get('error', None) if not result['success'] else None
                    })
                    
                    # Sleep briefly between harvests
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing farm {farm.id}: {str(e)}")
                    results['failed'] += 1
                    results['details'].append({
                        'farm_id': farm.id,
                        'chain': farm.chain,
                        'protocol': farm.protocol,
                        'pool': farm.pool_name,
                        'success': False,
                        'error': str(e)
                    })
            
            # Send alert with summary
            send_alert(f"🌾 Auto-harvest complete. {results['successful']} successful, {results['failed']} failed.")
            
            return {
                'success': True,
                'results': results,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error in manual harvest: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def check_farm_status(self, farm_id):
        """Check the status of a specific farm
        
        Args:
            farm_id (int): ID of the farm to check
            
        Returns:
            dict: Status information
        """
        try:
            # Get farm from database
            farm = YieldFarm.query.get(farm_id)
            if not farm:
                return {
                    'success': False,
                    'error': f"Farm with ID {farm_id} not found"
                }
            
            # Calculate time since last harvest
            if farm.last_harvest:
                time_since_harvest = datetime.utcnow() - farm.last_harvest
                hours_since_harvest = time_since_harvest.total_seconds() / 3600
            else:
                time_since_harvest = datetime.utcnow() - farm.start_date
                hours_since_harvest = time_since_harvest.total_seconds() / 3600
            
            # Calculate estimated current value
            time_elapsed = (datetime.utcnow() - farm.start_date).total_seconds() / (365 * 24 * 60 * 60)  # years
            estimated_interest = farm.deposit_amount * (farm.apy / 100) * time_elapsed
            estimated_current_value = farm.deposit_amount + estimated_interest
            
            return {
                'success': True,
                'farm_id': farm.id,
                'chain': farm.chain,
                'protocol': farm.protocol,
                'pool': farm.pool_name,
                'status': farm.status,
                'deposit_amount': farm.deposit_amount,
                'current_value': farm.current_value,
                'estimated_current_value': estimated_current_value,
                'apy': farm.apy,
                'start_date': farm.start_date.isoformat(),
                'last_harvest': farm.last_harvest.isoformat() if farm.last_harvest else None,
                'hours_since_harvest': hours_since_harvest,
                'needs_harvest': hours_since_harvest > 24  # Assume harvest needed after 24 hours
            }
            
        except Exception as e:
            logger.error(f"Error checking farm status: {str(e)}")
            
            return {
                'success': False,
                'error': str(e)
            }