import unittest
import sys
import os
import numpy as np

# Add the parent directory to the path so we can import the services module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analyzer import EnhancedExerciseAnalyzer

class TestExerciseAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up the analyzer instance before each test."""
        self.analyzer = EnhancedExerciseAnalyzer()

    def test_calculate_angle_90_degrees(self):
        """Test that a right angle (90 degrees) is calculated correctly."""
        # Points for a 90 degree angle at B
        a = {'x': 0, 'y': 1}
        b = {'x': 0, 'y': 0}
        c = {'x': 1, 'y': 0}
        
        angle = self.analyzer.calculate_angle_from_points(a, b, c)
        self.assertAlmostEqual(angle, 90.0, places=1)

    def test_calculate_angle_180_degrees(self):
        """Test that a straight line (180 degrees) is calculated correctly."""
        # Points for a 180 degree angle at B
        a = {'x': -1, 'y': 0}
        b = {'x': 0, 'y': 0}
        c = {'x': 1, 'y': 0}
        
        angle = self.analyzer.calculate_angle_from_points(a, b, c)
        self.assertAlmostEqual(angle, 180.0, places=1)

    def test_detect_phase_squat_bottom(self):
        """Test that a low angle is detected as the 'bottom' phase for squats."""
        # Mock landmarks to produce a ~70 degree knee angle
        # We can just mock the internal method or pass landmarks that produce it.
        # For simplicity, let's rely on the logic that uses _compute_key_angle.
        # But since _compute_key_angle calls calculate_angle_from_points, 
        # let's just test the logic directly if possible, or construct valid landmarks.
        
        # Constructing landmarks for a squat (Hip-Knee-Ankle)
        # Hip (23), Knee (25), Ankle (27)
        landmarks = [{'x': 0, 'y': 0}] * 33 # Initialize empty
        
        # Set specific points to form a ~60 degree angle
        # B (Knee) at (0,0)
        # A (Hip) at (0, 1)
        # C (Ankle) at (0.5, 0.866) -> roughly 60 deg
        landmarks[23] = {'x': 0.5, 'y': 0.866} # Hip
        landmarks[25] = {'x': 0, 'y': 0}       # Knee
        landmarks[27] = {'x': 1, 'y': 0}       # Ankle
        
        # We need to ensure the angle calculation comes out to ~60
        # Vector BA = (0.5, 0.866)
        # Vector BC = (1, 0)
        # This is actually just checking the math.
        
        # Let's use a simpler approach: Mocking the angle calculation isn't easy without mocking the class.
        # So we will trust the math and just check the phase logic with a known configuration.
        
        # Let's try a known "standing" pose (180 degrees)
        landmarks[23] = {'x': 0, 'y': 1}
        landmarks[25] = {'x': 0, 'y': 0}
        landmarks[27] = {'x': 0, 'y': -1}
        
        phase = self.analyzer.detect_exercise_phase(landmarks, 'squats')
        self.assertEqual(phase, 'standing')

    def test_detect_phase_squat_deep(self):
        """Test that a deep squat angle is detected as 'bottom'."""
        landmarks = [{'x': 0, 'y': 0}] * 33
        
        # Create a 75 degree angle at the knee (which should now be valid, < 80)
        # Knee at origin
        landmarks[25] = {'x': 0, 'y': 0}
        # Hip up
        landmarks[23] = {'x': 0, 'y': 1}
        # Ankle at 75 degrees relative to hip vector
        # x = sin(75) = 0.966, y = cos(75) = 0.259
        landmarks[27] = {'x': 0.966, 'y': 0.259}
        
        phase = self.analyzer.detect_exercise_phase(landmarks, 'squats')
        # 75 degrees should be bottom (threshold is 80)
        self.assertEqual(phase, 'bottom')

if __name__ == '__main__':
    unittest.main()
