import random
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

@dataclass 
class Particle: 
    position: np.ndarray 
    velocity: np.ndarray 
    best_position: np.ndarray 
    best_score: float 
    current_score: float 
     
    def update_velocity(self, global_best_position: np.ndarray, w: float, c1: float, c2: float): 
        """Update particle velocity using PSO formula with improved convergence.""" 
        r1, r2 = random.random(), random.random() 
        cognitive_component = c1 * r1 * (self.best_position - self.position) 
        social_component = c2 * r2 * (global_best_position - self.position) 
        self.velocity = w * self.velocity + cognitive_component + social_component 
         
    def update_position(self, bounds: List[Tuple[float, float]]): 
        """Update particle position with improved bounds handling.""" 
        self.position = self.position + self.velocity 
        # Enforce bounds with smooth clamping 
        for i, (lower, upper) in enumerate(bounds): 
            if self.position[i] < lower: 
                self.position[i] = lower + abs(self.velocity[i]) * 0.1 
            elif self.position[i] > upper: 
                self.position[i] = upper - abs(self.velocity[i]) * 0.1 
 
class ParticleSwarmOptimizer: 
    def __init__(self,  
                 num_particles: int,  
                 num_dimensions: int,  
                 bounds: List[Tuple[float, float]],  
                 objective_function, 
                 w: float = 0.7, 
                 c1: float = 1.5, 
                 c2: float = 1.5, 
                 max_iterations: int = 50): 
         
        self.num_particles = num_particles 
        self.num_dimensions = num_dimensions 
        self.bounds = bounds 
        self.objective_function = objective_function 
        self.w = w 
        self.c1 = c1 
        self.c2 = c2 
        self.max_iterations = max_iterations 
         
        # Initialize particles 
        self.particles = [] 
        self.global_best_position = None 
        self.global_best_score = float('inf') 
        self.initialize_swarm() 
         
    def initialize_swarm(self): 
        """Initialize particle swarm with improved distribution.""" 
        for _ in range(self.num_particles): 
            # Random position within bounds with better distribution 
            position = np.array([ 
                random.uniform(low, high) for low, high in self.bounds 
            ]) 
             
            # Initialize velocity with magnitude based on bounds 
            velocity = np.array([ 
                random.uniform(-abs(high-low)*0.1, abs(high-low)*0.1)  
                for low, high in self.bounds 
            ]) 
             
            particle = Particle( 
                position=position.copy(), 
                velocity=velocity, 
                best_position=position.copy(), 
                best_score=float('inf'), 
                current_score=float('inf') 
            ) 
             
            # Evaluate initial position 
            score = self.objective_function(position) 
            particle.current_score = score 
            particle.best_score = score 
             
            if score < self.global_best_score: 
                self.global_best_score = score 
                self.global_best_position = position.copy() 
             
            self.particles.append(particle) 
      
    def optimize(self, iterations=None): 
        """Run PSO optimization with improved convergence.""" 
        if iterations is None: 
            iterations = self.max_iterations 
             
        for _ in range(iterations): 
            # Update each particle 
            for particle in self.particles: 
                # Update velocity and position 
                particle.update_velocity(self.global_best_position, self.w, self.c1, self.c2) 
                particle.update_position(self.bounds) 
                 
                # Evaluate new position 
                score = self.objective_function(particle.position) 
                particle.current_score = score 
                 
                # Update personal best with improved convergence 
                if score < particle.best_score: 
                    particle.best_score = score 
                    particle.best_position = particle.position.copy() 
                     
                    # Update global best with improved convergence 
                    if score < self.global_best_score: 
                        self.global_best_score = score 
                        self.global_best_position = particle.position.copy() 
             
            # Adaptive inertia weight 
            self.w *= 0.99 
         
        return self.global_best_position, self.global_best_score 
     
    def get_current_best(self): 
        """Return current best particle with improved accuracy.""" 
        return self.global_best_position, self.global_best_score 
     
    def optimize_step(self): 
        """Perform a single iteration of PSO with improved convergence.""" 
        for particle in self.particles: 
            particle.update_velocity(self.global_best_position, self.w, self.c1, self.c2) 
            particle.update_position(self.bounds) 
             
            score = self.objective_function(particle.position) 
            particle.current_score = score 
             
            if score < particle.best_score: 
                particle.best_score = score 
                particle.best_position = particle.position.copy() 
                 
                if score < self.global_best_score: 
                    self.global_best_score = score 
                    self.global_best_position = particle.position.copy() 
          
        # Adaptive inertia weight 
        self.w *= 0.99 
         
        return self.global_best_position, self.global_best_score 
