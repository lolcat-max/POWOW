#!/usr/bin/env python3
"""
CUBE ROOT PoW - MINING THE NONCE ITSELF
=========================================

Hash ONLY the nonce (not the block data)
Find cube nonces whose hash has leading zeros
"""

import hashlib
import time

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def is_perfect_cube(n: int) -> tuple[bool, int]:
    """Check if n is a perfect cube"""
    if n == 0:
        return True, 0
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


def hash_nonce_only(nonce: int) -> str:
    # minimal number of bytes needed to represent nonce (at least 1)
    nbytes = max(1, (nonce.bit_length() + 7) // 8)
    nonce_bytes = nonce.to_bytes(nbytes, byteorder='big')
    return hashlib.sha256(nonce_bytes).hexdigest()


def verify_cube_nonce_pow(nonce: int, cube_difficulty: int, zero_difficulty: int) -> tuple[bool, str, int, str]:
    """
    Verify PoW where we hash ONLY the nonce:
    1. Nonce must be valid cube: cbrt(nonce) % cube_difficulty == 0
    2. Hash(nonce) must have leading zeros >= zero_difficulty
    
    Returns: (is_valid, hash, leading_zeros, reason)
    """
    # Check 1: Is nonce a valid cube?
    is_cube, cube_root = is_perfect_cube(nonce)
    if not is_cube:
        return False, "", 0, "Not a perfect cube"
    
    if (cube_root % cube_difficulty) != 0:
        return False, "", 0, f"Cube root {cube_root} not divisible by {cube_difficulty}"
    
    # Check 2: Does HASH(nonce) have enough leading zeros?
    hash_value = hash_nonce_only(nonce)
    zeros = count_leading_zeros(hash_value)
    
    if zeros < zero_difficulty:
        return False, hash_value, zeros, f"Only {zeros} zeros, need {zero_difficulty}"
    
    return True, hash_value, zeros, "Valid!"



def show_precomputed_nonces():
    """Show that you can precompute valid nonces"""
    
    print("\n" + "="*80)
    print("PRE-COMPUTED VALID NONCES (can be reused for any block!)")
    print("="*80)
    
    print("\nDifficulty: 10, Zero requirement: 1")
    print("\nSearching for valid cube nonces...\n")
    print(f"{'k':<8} {'Cube Root':<12} {'Nonce':<20} {'Hash(nonce)':<66} {'Zeros'}")
    print("-" * 120)
    
    found_count = 0
    for k in range(100000000, 1000000000):
        nonce = calculate_cube_nonce(6300, k)

            
        hash_val = hash_nonce_only(nonce)
        zeros = count_leading_zeros(hash_val)
        
        if zeros >= 8:
            cube_root = k * 10
            print(f"{k:<8} {cube_root:<12,} {nonce:<20,} {hash_val:<66} {zeros}")
            found_count += 1
            
            if found_count >= 10:
                break
    
    print(f"\n💡 These {found_count} nonces are ALWAYS valid (for any block)!")
    print("   You can store them and reuse them forever.")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + " CUBE ROOT PoW: MINING THE NONCE ITSELF ".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print("\n" + "="*80)
  

    show_precomputed_nonces()

if __name__ == "__main__":
    main()
