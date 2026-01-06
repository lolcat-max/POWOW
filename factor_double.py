#!/usr/bin/env python3
"""
CUBE ROOT PoW - MINING THE NONCE ITSELF (Updated to Double SHA-256)
=================================================================
"""

import hashlib
import time

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def is_perfect_cube(n: int) -> tuple[bool, int]:
    """Check if n is a perfect cube using integer-safe rounding"""
    if n == 0:
        return True, 0
    # Floating point precision may fail for nonces > 2^53; 
    # For a production system, use an integer-only root-finding algorithm.
    cube_root = round(n ** (1/3))
    if cube_root ** 3 == n:
        return True, cube_root
    return False, 0


def count_leading_zeros(hash_hex: str) -> int:
    """Count leading zeros in hex hash"""
    count = 0
    for char in hash_hex:
        if char == '0':
            count += 1
        else:
            break
    return count


def calculate_cube_nonce(difficulty: int, k: int) -> int:
    """Calculate k-th valid cube nonce: (k × difficulty)³"""
    return (k * difficulty) ** 3


def hash_nonce_only(nonce: int) -> tuple[bytes, str]:
    """
    Apply Double SHA-256 (SHA-256d) to the nonce.
    Returns: (pre-image bytes, double-sha-hex)
    """
    nonce += 2040
    # minimal number of bytes needed to represent nonce (at least 1)
    nbytes = max(1, (nonce.bit_length() + 7) // 8)
    prefix = b"HAHA"
    nonce_bytes = nonce.to_bytes(nbytes, byteorder='big')
    data = prefix + nonce_bytes

    # Double SHA-256: Hash the digest of the first pass
    first_pass = hashlib.sha256(data).digest()
    double_hash_hex = hashlib.sha256(first_pass).hexdigest()

    return data, double_hash_hex


def verify_cube_nonce_pow(nonce: int, cube_difficulty: int, zero_difficulty: int) -> tuple[bool, str, int, str]:
    """
    Verify PoW where we hash ONLY the nonce:
    1. Nonce must be valid cube: cbrt(nonce) % cube_difficulty == 0
    2. Hash(nonce) must have leading zeros >= zero_difficulty
    """
    # Check 1: Is nonce a valid cube?
    is_cube, cube_root = is_perfect_cube(nonce)
    if not is_cube:
        return False, "", 0, "Not a perfect cube"
    
    if (cube_root % cube_difficulty) != 0:
        return False, "", 0, f"Cube root {cube_root} not divisible by {cube_difficulty}"
    
    # Check 2: Does DOUBLE-HASH(nonce) have enough leading zeros?
    # Corrected unpacking: original script had a syntax error here
    _, hash_value = hash_nonce_only(nonce)
    zeros = count_leading_zeros(hash_value)
    
    if zeros < zero_difficulty:
        return False, hash_value, zeros, f"Only {zeros} zeros, need {zero_difficulty}"
    
    return True, hash_value, zeros, "Valid!"


def show_precomputed_nonces():
    """Show that you can precompute valid nonces with SHA-256d"""
    
    print("\n" + "="*80)
    print("PRE-COMPUTED VALID NONCES (Double SHA-256 Edition)")
    print("="*80)
    
    target_zeros = 6
    cube_diff = 630
    
    print(f"\nSearching for nonces with {target_zeros} leading zeros (SHA-256d)...")
    print(f"{'k':<8} {'Cube Root':<12} {'Nonce':<20} {'Double-Hash(nonce)':<66} {'Zeros'}")
    print("-" * 120)
    
    found_count = 0
    # Using a large range for k
    for k in range(1, 100000000):
        nonce = calculate_cube_nonce(cube_diff, k)

        header, hash_val = hash_nonce_only(nonce)
        zeros = count_leading_zeros(hash_val)
        
        if zeros >= target_zeros:
            cube_root = k * cube_diff
            print(f"{k:<8} {cube_root:<12,} {nonce:<20,} {hash_val:<66} {zeros}")
            found_count += 1
            
            if found_count >= 5: # Limit output for brevity
                break
    
    print(f"\n💡 These {found_count} nonces are ALWAYS valid for any block under this PoW.")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + " CUBE ROOT PoW: DOUBLE SHA-256 EDITION ".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    show_precomputed_nonces()

if __name__ == "__main__":
    main()
