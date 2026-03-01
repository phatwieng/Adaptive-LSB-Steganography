import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)

def analyze_frequency_signature(orig, stego):
    """Analyzes DCT energy shifts to detect embedding artifacts."""
    try:
        def get_energy(img):
            g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            f = np.abs(cv2.dct(g.astype(np.float32)))
            return f
        
        e1, e2 = get_energy(orig), get_energy(stego)
        diff = np.abs(e2 - e1)
        
        # Fidelity: 1.0 is perfect, lower is disturbed
        fidelity = 1.0 - (np.sum(diff) / (np.sum(e1) + 1e-10))
        return {
            'mean_energy_shift': float(np.mean(diff)),
            'frequency_fidelity': float(np.clip(fidelity, 0.0, 1.0))
        }
    except: return {'mean_energy_shift': 0.0, 'frequency_fidelity': 1.0}
