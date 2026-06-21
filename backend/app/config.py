# Configuration parameters for Traffic Management System

SUMO_CONFIG = { 
    'gui': True, 
    'config_file': r'C:\Users\ghana\OneDrive\Desktop\greenwave\broh.sumocfg', 
    'net_file': r'C:\Users\ghana\OneDrive\Desktop\greenwave\broh.net.xml', 
    'route_file': r'C:\Users\ghana\OneDrive\Desktop\greenwave\broh.rou.xml',  
} 
 
OPTIMIZATION_INTERVAL = 30 
CONGESTION_THRESHOLDS = { 
    'free_flow': 0.15,    
    'moderate': 0.35,    
    'heavy': 0.65,         
    'severe': 0.8,        
    'gridlock': 0.9 
} 
 
SPEED_LIMITS = { 
    'urban': 14.0, 
    'arterial': 17.0, 
    'highway': 28.0, 
    'residential': 8.5, 
    'bus_lane': 14.0 
} 
 
PCU_VALUES = { 
    'passenger': 1.0, 
    'truck': 2.3, 
    'trailer': 3.2, 
    'bus': 2.2, 
    'motorcycle': 0.4, 
    'bicycle': 0.2 
} 
 
PRIORITY_WEIGHTS = { 
    'bus': 3.5, 
    'truck': 2.2, 
    'passenger': 1.0, 
    'motorcycle': 0.8, 
    'bicycle': 0.8 
} 
 
MAX_REROUTE_ATTEMPTS = 4 
MIN_REROUTE_INTERVAL = 180 
CONGESTION_HISTORY_SIZE = 40 
ADAPTIVE_ROUTING_THRESHOLD = 0.65 
 
MIN_GREEN_TIME = 20 
MAX_GREEN_TIME = 100 
YELLOW_TIME = 4 
ALL_RED_TIME = 3 
 
PSO_PARTICLES = 15 
PSO_ITERATIONS = 7 
