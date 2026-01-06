import pyopencl as cl
import numpy as np

def run_opencl_miner(target_zeros=8, cube_diff=6300000, total_k=100000000000):
    # Context and Queue setup
    platforms = cl.get_platforms()
    devs = platforms[0].get_devices() # Adjust index if needed for your AMD device
    ctx = cl.Context(devs)
    queue = cl.CommandQueue(ctx)
    
    with open("sha256_cube.cl", "r") as f:
        prg = cl.Program(ctx, f.read()).build()

    # FIX 1: Create an explicit Kernel object to avoid 'RepeatedKernelRetrieval'
    knl = cl.Kernel(prg, "mine_cube")

    # FIX 2: Explicitly set scalar dtypes to prevent 'INVALID_VALUE'
    # Use np.uint64 for start_k and np.uint32 for others.
    knl.set_scalar_arg_dtypes([None, np.uint32, np.uint32, np.uint64])

    # Results buffer (91 uints = 1 count + 10 matches * (1 k-offset + 8 hash words))
    res_np = np.zeros(91, dtype=np.uint32)
    res_g = cl.Buffer(ctx, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=res_np)

    batch_size = 1048576 
    print(f"Mining with target {target_zeros} zeros...")

    # Iterate through k-space
    for start_k in range(1, int(total_k), batch_size):
        # FIX: Pass all arguments directly into the kernel call.
        # This automatically handles setting arguments and enqueuing.
        knl(queue, (batch_size,), None, 
            res_g, 
            np.uint32(cube_diff), 
            np.uint32(target_zeros), 
            np.uint64(start_k))
        
        # Ensure the GPU has finished the batch before reading results
        cl.enqueue_copy(queue, res_np, res_g)
        
        if res_np[0] > 0:
            count = min(res_np[0], 10)
            for i in range(count):
                base = 1 + (i * 9)
                found_k = int(start_k) + int(res_np[base])
                
                # Big-endian display logic (Python handles the massive integer size)
                nonce_val = (found_k * cube_diff)**3 + 2040
                nbytes = max(1, (nonce_val.bit_length() + 7) // 8)
                data_hex = b"HAHA".hex() + nonce_val.to_bytes(nbytes, 'big').hex()
                hash_hex = "".join(f"{res_np[base + 1 + j]:08x}" for j in range(8))
                
                print(f"\n[MATCH FOUND] k={found_k}")
                print(f"Nonce Bytes: {nbytes}")
                print(f"Data Hex:    {data_hex}")
                print(f"Hash Hex:    {hash_hex}")
            
            # Reset atomic counter on GPU to 0 for next batch
            res_np[0] = 0
            cl.enqueue_copy(queue, res_g, res_np[:1])
            
        # Clean up the command queue for the next batch
        queue.finish()


if __name__ == "__main__":
    run_opencl_miner()
