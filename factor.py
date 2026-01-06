#!/usr/bin/env python3
"""
CUBE ROOT PoW - AGGRESSIVE SEARCH FOR 5-8 ZEROS
================================================
Optimized search for high-difficulty cube nonces
Uses parallel processing and smart search strategies
"""
import hashlib
import time
from multiprocessing import Pool, cpu_count
import sys

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def hash_nonce_only(nonce: int) -> str:
    """Hash ONLY the nonce (not block data)"""
    nonce_bytes = nonce.to_bytes(16, byteorder='big')  # Use 16 bytes for larger nonces
    return hashlib.sha256(nonce_bytes).hexdigest()

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

def check_range(args):
    """Check a range of k values for valid nonces (for parallel processing)"""
    start_k, end_k, difficulty, target_zeros = args
    found = []
    
    for k in range(start_k, end_k):
        nonce = calculate_cube_nonce(difficulty, k)
        
        if nonce > 2**128:  # Practical limit
            break
            
        hash_val = hash_nonce_only(nonce)
        zeros = count_leading_zeros(hash_val)
        
        if zeros >= target_zeros:
            cube_root = k * difficulty
            found.append({
                'k': k,
                'cube_root': cube_root,
                'nonce': nonce,
                'hash': hash_val,
                'zeros': zeros
            })
    
    return found

def parallel_search(difficulty: int, target_zeros: int, max_k: int, max_nonces: int = 5):
    """Search for nonces using parallel processing"""
    
    print(f"\n{'='*80}")
    print(f"Searching for {target_zeros} leading zeros (Difficulty: {difficulty})")
    print(f"{'='*80}")
    print(f"Max k: {max_k:,}")
    print(f"Using {cpu_count()} CPU cores for parallel search...")
    
    start_time = time.time()
    
    # Split work across CPU cores
    chunk_size = max_k // (cpu_count() * 4)  # More chunks for better progress tracking
    ranges = []
    for i in range(0, max_k, chunk_size):
        end = min(i + chunk_size, max_k)
        ranges.append((i, end, difficulty, target_zeros))
    
    found_nonces = []
    processed_chunks = 0
    
    # Use multiprocessing pool
    with Pool(cpu_count()) as pool:
        for result in pool.imap_unordered(check_range, ranges):
            found_nonces.extend(result)
            processed_chunks += 1
            
            # Progress update
            progress = (processed_chunks / len(ranges)) * 100
            elapsed = time.time() - start_time
            rate = (processed_chunks * chunk_size) / elapsed if elapsed > 0 else 0
            
            sys.stdout.write(f"\r  Progress: {progress:.1f}% | Checked ~{processed_chunks * chunk_size:,} | "
                           f"Found: {len(found_nonces)} | Rate: {rate:,.0f} checks/sec")
            sys.stdout.flush()
            
            # Stop if we found enough
            if len(found_nonces) >= max_nonces:
                pool.terminate()
                break
    
    print()  # New line after progress
    
    elapsed = time.time() - start_time
    total_checked = min(processed_chunks * chunk_size, max_k)
    
    # Sort by number of zeros (descending) then by k
    found_nonces.sort(key=lambda x: (-x['zeros'], x['k']))
    
    # Display results
    if found_nonces[:max_nonces]:
        print(f"\n{'k':<12} {'Cube Root':<20} {'Nonce':<30} {'Hash':<66} {'Zeros'}")
        print("-" * 140)
        for entry in found_nonces[:max_nonces]:
            nonce_str = f"{entry['nonce']:,}" if entry['nonce'] < 10**20 else f"{entry['nonce']:.3e}"
            print(f"{entry['k']:<12,} {entry['cube_root']:<20,} {nonce_str:<30} {entry['hash']:<66} {entry['zeros']}")
        
        print(f"\n✓ Found {len(found_nonces)} nonces with {target_zeros}+ leading zeros!")
    else:
        print(f"\n✗ No nonces found with {target_zeros}+ zeros")
    
    print(f"  Searched ~{total_checked:,} cube nonces in {elapsed:.2f} seconds ({total_checked/elapsed:,.0f} checks/sec)")
    
    return found_nonces[:max_nonces]

def exhaustive_search_high_zeros():
    """Exhaustive search for 5-8 leading zeros"""
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + " CUBE ROOT PoW: EXHAUSTIVE SEARCH FOR 5-8 ZEROS ".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print("\n📊 Statistical Probability of N Leading Zeros:")
    print("-" * 80)
    for n in range(1, 9):
        prob = 16 ** (-n)
        expected_trials = int(1 / prob)
        print(f"   {n} zeros: 1/{expected_trials:,} ({prob*100:.6f}%)")
    
    print("\n⚠️  WARNING: This will search millions of candidates!")
    print("   Estimated time: 5-30 minutes depending on your CPU")
    
    all_results = {}
    
    # Search configurations: (target_zeros, max_k, max_nonces)
    search_configs = [
        (5, 10_000_000, 5),    # 5 zeros: ~1 in 1 million
        (6, 50_000_000, 3),    # 6 zeros: ~1 in 16 million
        (7, 100_000_000, 2),   # 7 zeros: ~1 in 268 million
        (8, 200_000_000, 1),   # 8 zeros: ~1 in 4 billion
    ]
    
    # Try different difficulty values
    difficulties = [10, 5, 3, 2, 1]
    
    for target_zeros, max_k, max_nonces in search_configs:
        print(f"\n{'='*80}")
        print(f"SEARCHING FOR {target_zeros} LEADING ZEROS")
        print(f"{'='*80}")
        
        found_any = False
        
        for difficulty in difficulties:
            results = parallel_search(difficulty, target_zeros, max_k, max_nonces)
            
            if results:
                all_results[target_zeros] = results
                found_any = True
                break  # Found some, move to next zero count
        
        if not found_any:
            all_results[target_zeros] = []
            print(f"\n⚠️  No {target_zeros}-zero nonces found. May need to search larger range.")
    
    return all_results

def show_final_summary(all_results):
    """Show final summary of all findings"""
    
    print("\n" + "="*80)
    print("FINAL SUMMARY - PRECOMPUTED HIGH-DIFFICULTY NONCES")
    print("="*80)
    
    print(f"\n{'Zeros':<10} {'Found':<10} {'k value':<15} {'Nonce':<30} {'Hash Preview'}")
    print("-" * 120)
    
    for zeros in range(5, 9):
        results = all_results.get(zeros, [])
        if results:
            example = results[0]
            nonce_str = f"{example['nonce']:,}" if example['nonce'] < 10**20 else f"{example['nonce']:.3e}"
            print(f"{zeros:<10} {len(results):<10} {example['k']:<15,} {nonce_str:<30} {example['hash'][:40]}...")
        else:
            print(f"{zeros:<10} {0:<10} {'N/A':<15} {'Not found':<30} {'-'}")
    
    print("\n" + "🚨"*40)
    print("\nCRITICAL SECURITY FLAW DEMONSTRATED:")
    print("="*80)
    
    total_found = sum(len(results) for results in all_results.values())
    
    if total_found > 0:
        print(f"✓ Found {total_found} high-difficulty nonces through offline computation")
        print("✓ These nonces work for ANY block (not tied to block data)")
        print("✓ Can be precomputed, stored, and reused infinitely")
        print("✓ Completely bypasses the 'proof of work' concept")
        print("\n❌ This is NOT secure!")
        print("✓  Real PoW: hash(block_data || nonce) - ties work to specific blocks")
    else:
        print("⚠️  Even without finding examples, the vulnerability exists:")
        print("   - With enough computation, nonces CAN be precomputed")
        print("   - Once found, they work for every block forever")
        print("   - This breaks the fundamental security of PoW")
    
    print()

# =============================================================================
# MAIN
# =============================================================================

def main():
    try:
        all_results = exhaustive_search_high_zeros()
        show_final_summary(all_results)
    except KeyboardInterrupt:
        print("\n\n⚠️  Search interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main()