import pygame
import random
import time
import threading
import sys
from enum import Enum
import math

# Initialize pygame
pygame.init()
pygame.font.init()
pygame.mixer.init()

# Screen dimensions
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Advanced Traffic Simulation")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
AMBER = (255, 191, 0)
LIGHT_BLUE = (135, 206, 235)  # For cleaner sky background
GRASS_GREEN = (34, 139, 34)   # For roadside areas

# Simulation parameters
FPS = 60
SIMULATION_TIME = 300  # seconds
DEFAULT_GREEN = 20
DEFAULT_YELLOW = 5
DEFAULT_RED = 150
MIN_GREEN = 10
MAX_GREEN = 60
STOP_LINE_OFFSET = 50  # Distance from intersection center to stop line
VEHICLE_GAP = 120      # Increased minimum gap between vehicles (was implicitly smaller)

# Vehicle types with properties
class VehicleType(Enum):
    SEDAN = {"name": "Sedan", "color": RED, "width": 40, "height": 20, "speed": 2.5, "acceleration": 0.2}
    SUV = {"name": "SUV", "color": (50, 50, 150), "width": 45, "height": 22, "speed": 2.3, "acceleration": 0.18}
    TRUCK = {"name": "Truck", "color": (200, 200, 0), "width": 50, "height": 25, "speed": 2.0, "acceleration": 0.15}
    MOTORBIKE = {"name": "Motorbike", "color": BLUE, "width": 30, "height": 15, "speed": 3.0, "acceleration": 0.25}
    BUS = {"name": "Bus", "color": GREEN, "width": 55, "height": 30, "speed": 1.8, "acceleration": 0.12}
    AMBULANCE = {"name": "Ambulance", "color": WHITE, "width": 45, "height": 25, "speed": 3.5, "acceleration": 0.3}
    POLICE = {"name": "Police", "color": (0, 0, 150), "width": 45, "height": 25, "speed": 3.2, "acceleration": 0.28}
    TAXI = {"name": "Taxi", "color": AMBER, "width": 40, "height": 20, "speed": 2.7, "acceleration": 0.22}

# Directions
class Direction(Enum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

# Traffic Signal class
class TrafficSignal:
    def __init__(self, red, yellow, green):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.total_green = 0
        self.signal_text = str(green)
        self.state = "red"  # red, yellow, green

# Vehicle class
class Vehicle(pygame.sprite.Sprite):
    def __init__(self, vehicle_type, direction, will_turn=False):
        super().__init__()
        self.type = vehicle_type
        self.direction = direction
        self.will_turn = will_turn
        self.turning = False
        self.turn_progress = 0
        self.crossed = False
        self.current_speed = 0
        self.max_speed = vehicle_type.value["speed"]
        self.acceleration = vehicle_type.value["acceleration"]
        self.braking = False
        self.headlights_on = False
        self.name = vehicle_type.value["name"]
        self.id = f"{self.name}-{random.randint(1000, 9999)}"
        
        # Emergency vehicle flag
        self.is_emergency = vehicle_type in [VehicleType.AMBULANCE, VehicleType.POLICE]
        
        # Create vehicle surface
        width = vehicle_type.value["width"]
        height = vehicle_type.value["height"]
        self.original_image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.original_image.fill(vehicle_type.value["color"])
        
        # Add vehicle details
        self.add_vehicle_details()
        
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        
        # Set initial position based on direction
        self.set_initial_position()
        
        # Set stop line position
        self.stop_line = self.calculate_stop_line()
        
        # For turning vehicles
        self.turn_direction = random.choice(["left", "right"])
        self.turn_radius = 60
        self.turn_center = (0, 0)
        
        # For emergency vehicles
        self.siren_on = self.is_emergency
        self.siren_phase = 0
        self.siren_colors = [RED, BLUE]
        
        # For headlights
        self.headlight_color = (255, 255, 200)
        self.headlight_offset = 5
        
    def add_vehicle_details(self):
        """Add identifying details to the vehicle"""
        # Add license plate
        plate_color = (200, 200, 200) if not self.is_emergency else (255, 255, 255)
        pygame.draw.rect(self.original_image, plate_color, 
                        (5, self.original_image.get_height() - 8, 
                         self.original_image.get_width() - 10, 6))
        
        # Add license plate text
        font = pygame.font.SysFont('Arial', 8)
        plate_text = font.render(self.id[-4:], True, BLACK)
        self.original_image.blit(plate_text, (10, self.original_image.get_height() - 10))
        
        # Add special markings for emergency vehicles
        if self.type == VehicleType.AMBULANCE:
            pygame.draw.rect(self.original_image, RED, (5, 5, self.original_image.get_width() - 10, 10))
            font = pygame.font.SysFont('Arial', 10)
            text = font.render("EMS", True, WHITE)
            self.original_image.blit(text, (10, 5))
        elif self.type == VehicleType.POLICE:
            font = pygame.font.SysFont('Arial', 10)
            text = font.render("POLICE", True, WHITE)
            self.original_image.blit(text, (5, 5))
        elif self.type == VehicleType.TAXI:
            font = pygame.font.SysFont('Arial', 10)
            text = font.render("TAXI", True, BLACK)
            self.original_image.blit(text, (10, 5))
    
    def set_initial_position(self):
        """Set the vehicle's initial position based on its direction"""
        lane_offset = random.randint(-30, 30)
        
        if self.direction == Direction.NORTH:
            self.rect.centerx = SCREEN_WIDTH // 2 - 50 + lane_offset  # Left side of road
            self.rect.centery = SCREEN_HEIGHT + 50
            self.angle = 0
        elif self.direction == Direction.EAST:
            self.rect.centerx = -50
            self.rect.centery = SCREEN_HEIGHT // 2 - 50 + lane_offset  # Upper side of road
            self.angle = 270
        elif self.direction == Direction.SOUTH:
            self.rect.centerx = SCREEN_WIDTH // 2 + 50 + lane_offset  # Right side of road
            self.rect.centery = -50
            self.angle = 180
        elif self.direction == Direction.WEST:
            self.rect.centerx = SCREEN_WIDTH + 50
            self.rect.centery = SCREEN_HEIGHT // 2 + 50 + lane_offset  # Lower side of road
            self.angle = 90
        
        # Rotate image to face correct direction
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
    
    def calculate_stop_line(self):
        """Calculate the stop line position based on vehicle direction"""
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        if self.direction == Direction.NORTH:
            return (self.rect.centerx, center_y + STOP_LINE_OFFSET)
        elif self.direction == Direction.EAST:
            return (center_x - STOP_LINE_OFFSET, self.rect.centery)
        elif self.direction == Direction.SOUTH:
            return (self.rect.centerx, center_y - STOP_LINE_OFFSET)
        elif self.direction == Direction.WEST:
            return (center_x + STOP_LINE_OFFSET, self.rect.centery)
    
    def update(self, current_green, current_yellow):
        """Update vehicle position and state"""
        # Determine if we should stop (red or yellow light)
        should_stop = False
        if ((self.direction.value == current_green and not current_yellow) or self.is_emergency):
            # Green light or emergency vehicle - don't stop
            should_stop = False
        elif self.direction.value == current_green and current_yellow:
            # Yellow light - stop if we can't make it through
            dist_to_intersection = self.distance_to_intersection()
            stopping_distance = (self.current_speed ** 2) / (2 * self.acceleration * 2)  # Physics-based stopping
            should_stop = dist_to_intersection > stopping_distance
        else:
            # Red light - stop
            should_stop = True
        
        # Emergency vehicles ignore some rules
        if self.is_emergency:
            should_stop = False
        
        # Adjust speed based on whether we should stop
        if should_stop and not self.crossed:
            # Need to stop at the stop line
            dist_to_stop = self.distance_to_stop_line()
            if dist_to_stop > 0:
                # Calculate required deceleration to stop at the line
                if dist_to_stop < (self.current_speed ** 2) / (2 * self.acceleration * 3):
                    self.current_speed = max(0, self.current_speed - self.acceleration * 3)
                else:
                    # Accelerate toward the stop line
                    self.current_speed = min(self.max_speed, self.current_speed + self.acceleration)
            else:
                # At or past the stop line
                self.current_speed = 0
                self.crossed = True
        else:
            # Accelerate to max speed
            self.current_speed = min(self.max_speed, self.current_speed + self.acceleration)
        
        # Move the vehicle
        self.move_vehicle()
        
        # Update headlights and siren
        self.update_lights()
        
        # Check if vehicle is out of bounds
        if self.is_out_of_bounds():
            self.kill()
    
    def detect_emergency_ahead(self, vehicles):
        """Detect emergency vehicles ahead and adjust behavior"""
        if self.is_emergency:  # Emergency vehicles don't need to adjust
            return
            
        # Check for emergency vehicles in the same direction
        for vehicle in vehicles:
            if vehicle.is_emergency and vehicle.direction == self.direction:
                # If emergency vehicle is behind this vehicle
                if (self.direction == Direction.NORTH and vehicle.rect.centery > self.rect.centery) or \
                   (self.direction == Direction.EAST and vehicle.rect.centerx < self.rect.centerx) or \
                   (self.direction == Direction.SOUTH and vehicle.rect.centery < self.rect.centery) or \
                   (self.direction == Direction.WEST and vehicle.rect.centerx > self.rect.centerx):
                    # Calculate distance between vehicles
                    if self.direction == Direction.NORTH or self.direction == Direction.SOUTH:
                        distance = abs(vehicle.rect.centery - self.rect.centery)
                    else:
                        distance = abs(vehicle.rect.centerx - self.rect.centerx)
                    
                    # Only respond if emergency vehicle is close enough
                    if distance < 200:
                        # Slow down and move to the side
                        self.current_speed = max(0, self.current_speed - self.acceleration * 2)
                        
                        # Move to the right side of the lane
                        if self.direction == Direction.NORTH or self.direction == Direction.SOUTH:
                            self.rect.centerx += 20 if self.rect.centerx < SCREEN_WIDTH // 2 else -20
                        else:
                            self.rect.centery += 20 if self.rect.centery < SCREEN_HEIGHT // 2 else -20
    
    def distance_to_stop_line(self):
        """Calculate distance to stop line"""
        if self.direction == Direction.NORTH:
            return self.stop_line[1] - self.rect.centery
        elif self.direction == Direction.EAST:
            return self.rect.centerx - self.stop_line[0]
        elif self.direction == Direction.SOUTH:
            return self.rect.centery - self.stop_line[1]
        elif self.direction == Direction.WEST:
            return self.stop_line[0] - self.rect.centerx
    
    def distance_to_intersection(self):
        """Calculate distance to intersection center"""
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        if self.direction == Direction.NORTH:
            return center_y - self.rect.centery
        elif self.direction == Direction.EAST:
            return self.rect.centerx - center_x
        elif self.direction == Direction.SOUTH:
            return self.rect.centery - center_y
        elif self.direction == Direction.WEST:
            return center_x - self.rect.centerx
    
    def move_vehicle(self):
        """Move the vehicle based on its direction and speed"""
        if self.turning:
            self.execute_turn()
        else:
            # Straight movement
            if self.direction == Direction.NORTH:
                self.rect.centery -= self.current_speed
            elif self.direction == Direction.EAST:
                self.rect.centerx += self.current_speed
            elif self.direction == Direction.SOUTH:
                self.rect.centery += self.current_speed
            elif self.direction == Direction.WEST:
                self.rect.centerx -= self.current_speed
            
            # Check if we should start turning
            if self.will_turn and not self.turning and self.crossed:
                dist_to_center = self.distance_to_intersection()
                if abs(dist_to_center) < 30:  # Close enough to center to start turn
                    self.start_turn()
    
    def start_turn(self):
        """Initialize turning parameters"""
        self.turning = True
        self.turn_progress = 0
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        # Determine turn center based on direction and turn type
        if self.direction == Direction.NORTH:
            if self.turn_direction == "left":
                self.turn_center = (center_x - self.turn_radius, center_y - self.turn_radius)
            else:
                self.turn_center = (center_x + self.turn_radius, center_y - self.turn_radius)
        elif self.direction == Direction.EAST:
            if self.turn_direction == "left":
                self.turn_center = (center_x + self.turn_radius, center_y - self.turn_radius)
            else:
                self.turn_center = (center_x + self.turn_radius, center_y + self.turn_radius)
        elif self.direction == Direction.SOUTH:
            if self.turn_direction == "left":
                self.turn_center = (center_x + self.turn_radius, center_y + self.turn_radius)
            else:
                self.turn_center = (center_x - self.turn_radius, center_y + self.turn_radius)
        elif self.direction == Direction.WEST:
            if self.turn_direction == "left":
                self.turn_center = (center_x - self.turn_radius, center_y + self.turn_radius)
            else:
                self.turn_center = (center_x - self.turn_radius, center_y - self.turn_radius)
    
    def execute_turn(self):
        """Execute the turning maneuver"""
        self.turn_progress += self.current_speed / 2
        
        # Calculate new position along circular path
        angle = math.radians(self.turn_progress)
        if self.turn_direction == "left":
            angle = -angle
        
        # Determine which quarter-circle we're on based on original direction
        if self.direction == Direction.NORTH:
            if self.turn_direction == "left":
                # Turning west (left from north)
                new_x = self.turn_center[0] + self.turn_radius * math.cos(angle + math.pi/2)
                new_y = self.turn_center[1] + self.turn_radius * math.sin(angle + math.pi/2)
                new_angle = math.degrees(angle + math.pi/2)
            else:
                # Turning east (right from north)
                new_x = self.turn_center[0] + self.turn_radius * math.cos(angle - math.pi/2)
                new_y = self.turn_center[1] + self.turn_radius * math.sin(angle - math.pi/2)
                new_angle = math.degrees(angle - math.pi/2)
        elif self.direction == Direction.EAST:
            if self.turn_direction == "left":
                # Turning north (left from east)
                new_x = self.turn_center[0] + self.turn_radius * math.cos(angle + math.pi)
                new_y = self.turn_center[1] + self.turn_radius * math.sin(angle + math.pi)
                new_angle = math.degrees(angle + math.pi)
            else:
                # Turning south (right from east)
                new_x = self.turn_center[0] + self.turn_radius * math.cos(angle)
                new_y = self.turn_center[1] + self.turn_radius * math.sin(angle)
                new_angle = math.degrees(angle)
        elif self.direction == Direction.SOUTH:
            if self.turn_direction == "left":
                # Turning east (left from south)
                new_x = self.turn_center[0] + self.turn_radius * math.cos(angle - math.pi/2)
                new_y = self.turn_center[1] + self.turn_radius * math.sin(angle - math.pi/2)
                new_angle = math.degrees(angle - math.pi/2)
            else:
                # Turning west (right from south)
                new_x = self.turn_center[0] + self.turn_radius * math.cos(angle + math.pi/2)
                new_y = self.turn_center[1] + self.turn_radius * math.sin(angle + math.pi/2)
                new_angle = math.degrees(angle + math.pi/2)
        elif self.direction == Direction.WEST:
            if self.turn_direction == "left":
                # Turning south (left from west)
                new_x = self.turn_center[0] + self.turn_radius * math.cos(angle)
                new_y = self.turn_center[1] + self.turn_radius * math.sin(angle)
                new_angle = math.degrees(angle)
            else:
                # Turning north (right from west)
                new_x = self.turn_center[0] + self.turn_radius * math.cos(angle + math.pi)
                new_y = self.turn_center[1] + self.turn_radius * math.sin(angle + math.pi)
                new_angle = math.degrees(angle + math.pi)
        
        # Update position and rotation
        self.rect.centerx = new_x
        self.rect.centery = new_y
        self.angle = new_angle
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        
        # Check if turn is complete (90 degrees)
        if self.turn_progress >= 90:
            self.turning = False
            self.will_turn = False
            # Update direction after turn
            if self.direction == Direction.NORTH:
                self.direction = Direction.WEST if self.turn_direction == "left" else Direction.EAST
            elif self.direction == Direction.EAST:
                self.direction = Direction.NORTH if self.turn_direction == "left" else Direction.SOUTH
            elif self.direction == Direction.SOUTH:
                self.direction = Direction.EAST if self.turn_direction == "left" else Direction.WEST
            elif self.direction == Direction.WEST:
                self.direction = Direction.SOUTH if self.turn_direction == "left" else Direction.NORTH
            self.stop_line = self.calculate_stop_line()
    
    def update_lights(self):
        """Update headlights and siren effects"""
        # Toggle headlights randomly (simulating night/day)
        if random.random() < 0.01:  # 1% chance to toggle
            self.headlights_on = not self.headlights_on
        
        # Update siren for emergency vehicles
        if self.siren_on:
            self.siren_phase = (self.siren_phase + 1) % 20
            if self.siren_phase == 0:
                # Add siren effect to vehicle image
                siren_color = self.siren_colors[0]
                self.siren_colors = [self.siren_colors[1], self.siren_colors[0]]
                temp_image = self.original_image.copy()
                pygame.draw.rect(temp_image, siren_color, 
                                (temp_image.get_width() - 15, 5, 10, 10))
                self.original_image = temp_image
                self.image = pygame.transform.rotate(self.original_image, -self.angle)
                self.rect = self.image.get_rect(center=self.rect.center)
    
    def draw_headlights(self, screen):
        """Draw vehicle headlights"""
        if self.headlights_on:
            # Calculate headlight positions based on vehicle direction
            if self.direction == Direction.NORTH:
                pos1 = (self.rect.centerx - 10, self.rect.centery + self.headlight_offset)
                pos2 = (self.rect.centerx + 10, self.rect.centery + self.headlight_offset)
            elif self.direction == Direction.EAST:
                pos1 = (self.rect.centerx - self.headlight_offset, self.rect.centery - 10)
                pos2 = (self.rect.centerx - self.headlight_offset, self.rect.centery + 10)
            elif self.direction == Direction.SOUTH:
                pos1 = (self.rect.centerx - 10, self.rect.centery - self.headlight_offset)
                pos2 = (self.rect.centerx + 10, self.rect.centery - self.headlight_offset)
            elif self.direction == Direction.WEST:
                pos1 = (self.rect.centerx + self.headlight_offset, self.rect.centery - 10)
                pos2 = (self.rect.centerx + self.headlight_offset, self.rect.centery + 10)
            
            # Draw headlight beams
            pygame.draw.circle(screen, self.headlight_color, pos1, 8)
            pygame.draw.circle(screen, self.headlight_color, pos2, 8)
    
    def is_out_of_bounds(self):
        """Check if vehicle is out of screen bounds"""
        return (self.rect.right < -50 or self.rect.left > SCREEN_WIDTH + 50 or
                self.rect.bottom < -50 or self.rect.top > SCREEN_HEIGHT + 50)

# Traffic Simulation class
class TrafficSimulation:
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.running = True
        self.time_elapsed = 0
        self.vehicles = pygame.sprite.Group()
        self.signals = []
        self.current_green = 0
        self.current_yellow = False
        self.night_mode = False
        self.ambulance_active = False
        self.emergency_override = False
        self.emergency_target = None
        self.sound_enabled = True
        
        # UI elements
        self.font = pygame.font.SysFont('Arial', 20)
        self.bg_color = LIGHT_BLUE  # Cleaner background
        
        # Emergency vehicle sirens and sounds
        self.siren_sound = pygame.mixer.Sound('siren.mp3') if pygame.mixer.get_init() else None
        self.siren_playing = False
        
        # Initialize traffic signals
        for i in range(4):
            self.signals.append(TrafficSignal(DEFAULT_RED, DEFAULT_YELLOW, DEFAULT_GREEN))
        
        # Start threads
        threading.Thread(target=self.generate_vehicles, daemon=True).start()
        threading.Thread(target=self.control_signals, daemon=True).start()
        threading.Thread(target=self.toggle_night_mode, daemon=True).start()
    
    def generate_vehicles(self):
        """Generate random vehicles at random intervals"""
        while self.running:
            try:
                # Check vehicle count - limit the number of vehicles to prevent overcrowding
                if len(self.vehicles) > 25:  # Maximum number of vehicles in simulation
                    time.sleep(1.0)
                    continue
                
                # Randomly select vehicle type (weighted toward common vehicles)
                vehicle_weights = [0.25, 0.2, 0.15, 0.15, 0.1, 0.05, 0.05, 0.05]
                vehicle_type = random.choices(list(VehicleType), weights=vehicle_weights)[0]
                
                # Randomly select direction
                direction = random.choice(list(Direction))
                
                # Check if there's enough space for a new vehicle in this direction
                if not self.check_vehicle_spacing(direction):
                    time.sleep(0.5)
                    continue
                
                # Randomly decide if vehicle will turn (20% chance)
                will_turn = random.random() < 0.2
                
                # Create vehicle
                vehicle = Vehicle(vehicle_type, direction, will_turn)
                self.vehicles.add(vehicle)
                
                # Random delay between vehicle generation - increased for less density
                time.sleep(random.uniform(0.5, 2.0))
            except Exception as e:
                print(f"Error generating vehicle: {e}")
                continue
    
    def check_vehicle_spacing(self, direction):
        """Check if there's enough space for a new vehicle in the given direction"""
        # Get all vehicles in this direction near the spawn point
        nearby_vehicles = []
        
        for vehicle in self.vehicles:
            if vehicle.direction == direction:
                if direction == Direction.NORTH and vehicle.rect.centery > SCREEN_HEIGHT - VEHICLE_GAP:
                    nearby_vehicles.append(vehicle)
                elif direction == Direction.EAST and vehicle.rect.centerx < VEHICLE_GAP:
                    nearby_vehicles.append(vehicle)
                elif direction == Direction.SOUTH and vehicle.rect.centery < VEHICLE_GAP:
                    nearby_vehicles.append(vehicle)
                elif direction == Direction.WEST and vehicle.rect.centerx > SCREEN_WIDTH - VEHICLE_GAP:
                    nearby_vehicles.append(vehicle)
        
        # If there are vehicles nearby, don't spawn a new one
        return len(nearby_vehicles) == 0
    
    def control_signals(self):
        """Control traffic signal timing and states"""
        while self.running:
            try:
                # Green phase
                self.signals[self.current_green].state = "green"
                while self.signals[self.current_green].green > 0:
                    self.signals[self.current_green].green -= 1
                    self.signals[self.current_green].signal_text = str(self.signals[self.current_green].green)
                    self.signals[self.current_green].total_green += 1
                    time.sleep(1)
                    
                    # Check if emergency override activates
                    if self.emergency_override:
                        break
                
                # Yellow phase
                self.current_yellow = True
                self.signals[self.current_green].state = "yellow"
                while self.signals[self.current_green].yellow > 0:
                    self.signals[self.current_green].yellow -= 1
                    self.signals[self.current_green].signal_text = str(self.signals[self.current_green].yellow)
                    time.sleep(1)
                    
                    # Check if emergency override activates
                    if self.emergency_override and self.signals[self.current_green].yellow > 2:
                        self.signals[self.current_green].yellow = 2
                self.current_yellow = False
                
                # Red phase
                self.signals[self.current_green].state = "red"
                
                # Reset signal times for next cycle
                self.signals[self.current_green].green = DEFAULT_GREEN
                self.signals[self.current_green].yellow = DEFAULT_YELLOW
                self.signals[self.current_green].red = DEFAULT_RED
                
                # Move to next signal (unless emergency override)
                if not self.emergency_override:
                    self.current_green = (self.current_green + 1) % 4
            except Exception as e:
                print(f"Error in signal control: {e}")
                continue
    
    def toggle_night_mode(self):
        """Randomly toggle night mode for visual variety"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            self.night_mode = random.random() < 0.3  # 30% chance to switch to night
    
    def check_emergency_vehicles(self):
        """Check for approaching emergency vehicles and adjust signals if needed"""
        emergency_vehicles = [v for v in self.vehicles if v.is_emergency]
        
        # If no emergency vehicles, return
        if not emergency_vehicles:
            self.ambulance_active = False
            if self.siren_playing and self.siren_sound:
                self.siren_sound.stop()
                self.siren_playing = False
            return
        
        # Check for emergency vehicles approaching the intersection
        approaching_emergency = False
        approaching_direction = None
        
        for vehicle in emergency_vehicles:
            dist_to_intersection = vehicle.distance_to_intersection()
            
            # If emergency vehicle is approaching the intersection (within 200 pixels)
        
            
            # If emergency vehicle is approaching the intersection (within 200 pixels)
            if 0 < dist_to_intersection < 200:
                approaching_emergency = True
                approaching_direction = vehicle.direction
                self.ambulance_active = True
                
                # Play siren sound if not already playing
                if self.sound_enabled and self.siren_sound and not self.siren_playing:
                    self.siren_sound.play(-1)  # Loop the sound
                    self.siren_playing = True
                break
        
        # Change traffic signals if emergency vehicle is approaching
        if approaching_emergency and approaching_direction is not None:
            target_green = approaching_direction.value
            
            # Only change if not already green for that direction
            if self.current_green != target_green and not self.emergency_override:
                self.emergency_override = True
                self.emergency_target = target_green
                
                # Force current signal to yellow
                if not self.current_yellow:
                    self.signals[self.current_green].green = 1
        else:
            if self.emergency_override:
                self.emergency_override = False
                if self.siren_playing and self.siren_sound:
                    self.siren_sound.stop()
                    self.siren_playing = False
    
    def handle_emergency_override(self):
        """Handle the emergency signal override process"""
        if self.emergency_override and self.emergency_target is not None:
            # If currently in yellow phase, wait for it to complete
            if self.current_yellow:
                return
                
            # Change to the emergency direction
            self.current_green = self.emergency_target
            self.signals[self.current_green].green = DEFAULT_GREEN
            self.signals[self.current_green].yellow = DEFAULT_YELLOW
            self.signals[self.current_green].red = DEFAULT_RED
            self.signals[self.current_green].state = "green"
    
    def draw_intersection(self):
        """Draw the intersection with roads and markings"""
        # Draw roads
        pygame.draw.rect(screen, GRAY, (400, 0, 600, SCREEN_HEIGHT))  # Vertical road
        pygame.draw.rect(screen, GRAY, (0, 300, SCREEN_WIDTH, 200))  # Horizontal road
        
        # Draw lane markings on vertical road
        for i in range(0, SCREEN_HEIGHT, 50):
            pygame.draw.rect(screen, YELLOW, (SCREEN_WIDTH // 2 - 5, i, 10, 30))
        
        # Draw lane markings on horizontal road
        for i in range(0, SCREEN_WIDTH, 50):
            pygame.draw.rect(screen, YELLOW, (i, SCREEN_HEIGHT // 2 - 5, 30, 10))
        
        # Draw intersection
        pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 100, 200, 200))
        
        # Draw stop lines
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        pygame.draw.line(screen, WHITE, (center_x - 150, center_y - STOP_LINE_OFFSET), 
                         (center_x - 50, center_y - STOP_LINE_OFFSET), 5)  # North
        pygame.draw.line(screen, WHITE, (center_x + STOP_LINE_OFFSET, center_y - 150), 
                         (center_x + STOP_LINE_OFFSET, center_y - 50), 5)  # East
        pygame.draw.line(screen, WHITE, (center_x + 50, center_y + STOP_LINE_OFFSET), 
                         (center_x + 150, center_y + STOP_LINE_OFFSET), 5)  # South
        pygame.draw.line(screen, WHITE, (center_x - STOP_LINE_OFFSET, center_y + 50), 
                         (center_x - STOP_LINE_OFFSET, center_y + 150), 5)  # West
    
    def draw_traffic_signals(self):
        """Draw traffic signals on the screen"""
        radius = 20
        # Signal positions (North, East, South, West)
        positions = [
            (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 100),  # North
            (SCREEN_WIDTH // 2 + 100, SCREEN_HEIGHT // 2 - 100),  # East
            (SCREEN_WIDTH // 2 + 100, SCREEN_HEIGHT // 2 + 100),  # South
            (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 100)   # West
        ]
        
        for i, signal in enumerate(self.signals):
            # Draw signal background
            pygame.draw.circle(screen, BLACK, positions[i], radius + 5)
            
            # Draw appropriate signal color
            if i == self.current_green and not self.current_yellow:
                color = GREEN
            elif i == self.current_green and self.current_yellow:
                color = YELLOW
            else:
                color = RED
            
            pygame.draw.circle(screen, color, positions[i], radius)
            
            # Draw countdown text
            font = pygame.font.SysFont('Arial', 15)
            text = font.render(signal.signal_text, True, BLACK)
            text_rect = text.get_rect(center=positions[i])
            screen.blit(text, text_rect)
    
    def draw_night_effects(self):
        """Apply night mode effects"""
        if self.night_mode:
            # Draw semi-transparent overlay for night effect
            night_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            night_overlay.fill((0, 0, 50, 100))  # Dark blue tint with alpha
            screen.blit(night_overlay, (0, 0))
            
            # Draw street lights
            for x in range(200, SCREEN_WIDTH, 300):
                pygame.draw.circle(screen, (255, 255, 150, 150), (x, 100), 50)
                pygame.draw.circle(screen, (255, 255, 150, 150), (x, SCREEN_HEIGHT - 100), 50)
            
            for y in range(200, SCREEN_HEIGHT, 300):
                pygame.draw.circle(screen, (255, 255, 150, 150), (100, y), 50)
                pygame.draw.circle(screen, (255, 255, 150, 150), (SCREEN_WIDTH - 100, y), 50)
    
    def draw_stats(self):
        """Draw simulation statistics"""
        font = pygame.font.SysFont('Arial', 20)
        
        # Draw time elapsed
        time_text = font.render(f"Time: {int(self.time_elapsed)} s", True, BLACK)
        screen.blit(time_text, (10, 10))
        
        # Draw vehicle count
        vehicle_count = len(self.vehicles)
        count_text = font.render(f"Vehicles: {vehicle_count}", True, BLACK)
        screen.blit(count_text, (10, 40))
        
        # Draw emergency status
        status_color = RED if self.ambulance_active else BLACK
        status_text = font.render("EMERGENCY VEHICLE APPROACHING" if self.ambulance_active else "", True, status_color)
        screen.blit(status_text, (SCREEN_WIDTH // 2 - 180, 10))
        
        # Draw day/night indicator
        mode_text = font.render("Night Mode" if self.night_mode else "Day Mode", True, BLACK)
        screen.blit(mode_text, (SCREEN_WIDTH - 150, 10))
    
    def detect_collisions(self):
        """Detect and handle vehicle collisions"""
        # Simple collision detection between vehicles
        all_vehicles = self.vehicles.sprites()
        
        for i, vehicle1 in enumerate(all_vehicles):
            for vehicle2 in all_vehicles[i+1:]:
                # Skip if vehicles are too far apart to collide
                distance = ((vehicle1.rect.centerx - vehicle2.rect.centerx) ** 2 + 
                           (vehicle1.rect.centery - vehicle2.rect.centery) ** 2) ** 0.5
                
                if distance > 50:  # Skip detailed collision check if too far
                    continue
                
                # Check if vehicles are colliding
                if pygame.sprite.collide_rect(vehicle1, vehicle2):
                    # Simplified collision response - just stop both vehicles
                    vehicle1.current_speed = 0
                    vehicle2.current_speed = 0
                    
                    # If one is emergency, let it continue
                    if vehicle1.is_emergency:
                        vehicle2.current_speed = 0
                        vehicle1.current_speed = vehicle1.max_speed / 2
                    elif vehicle2.is_emergency:
                        vehicle1.current_speed = 0
                        vehicle2.current_speed = vehicle2.max_speed / 2
    
    def update(self):
        """Update the simulation state"""
        # Check for emergency vehicles
        self.check_emergency_vehicles()
        
        # Handle emergency override
        self.handle_emergency_override()
        
        # Update all vehicles
        for vehicle in self.vehicles:
            vehicle.update(self.current_green, self.current_yellow)
            vehicle.detect_emergency_ahead(self.vehicles)
        
        # Check for collisions
        self.detect_collisions()
    
    def draw(self):
        """Draw all elements of the simulation"""
        # Fill background
        screen.fill(WHITE if not self.night_mode else BLACK)
        
        # Draw intersection
        self.draw_intersection()
        
        # Draw traffic signals
        self.draw_traffic_signals()
        
        # Draw all vehicles
        self.vehicles.draw(screen)
        
        # Draw vehicle headlights
        for vehicle in self.vehicles:
            vehicle.draw_headlights(screen)
        
        # Draw night effects
        if self.night_mode:
            self.draw_night_effects()
        
        # Draw statistics
        self.draw_stats()
        
        # Update display
        pygame.display.flip()
    
    def run(self):
        """Main simulation loop"""
        start_time = time.time()
        
        try:
            # Main game loop
            while self.running and self.time_elapsed < SIMULATION_TIME:
                # Event handling
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False
                        elif event.key == pygame.K_s:  # Toggle sound
                            self.sound_enabled = not self.sound_enabled
                            if not self.sound_enabled and self.siren_playing and self.siren_sound:
                                self.siren_sound.stop()
                                self.siren_playing = False
                
                # Update simulation
                self.update()
                
                # Draw everything
                self.draw()
                
                # Update elapsed time
                self.time_elapsed = time.time() - start_time
                
                # Cap the frame rate
                self.clock.tick(FPS)
        
        except Exception as e:
            print(f"Simulation error: {e}")
        
        finally:
            # Clean up
            if self.siren_sound and self.siren_playing:
                self.siren_sound.stop()
            self.running = False
            pygame.quit()

# Create and run the simulation
if __name__ == "__main__":
    try:
        simulation = TrafficSimulation()
        simulation.run()
    except Exception as e:
        print(f"Error starting simulation: {e}")
        pygame.quit()
        sys.exit(1)
    sys.exit(0)