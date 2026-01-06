import pyopencl as cl
import numpy as np

def run_opencl_miner(target_zeros=13, cube_diff=6300000000, total_k=100000000000000):
    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)
    
    with open("sha256_cube.cl", "r") as f:
        prg = cl.Program(ctx, f.read()).build()

    knl = cl.Kernel(prg, "mine_cube")

    # Inform PyOpenCL about the exact 64-bit and 32-bit types
    knl.set_scalar_arg_dtypes([None, np.uint64, np.uint32, np.uint64])

    res_np = np.zeros(91, dtype=np.uint32)
    res_g = cl.Buffer(ctx, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=res_np)

    batch_size = 1048576 
    print(f"Mining with target {target_zeros} zeros...")

    for start_k in range(1, int(total_k), batch_size):
        # Set arguments individually using numpy types to bypass Windows 32-bit long limits
        knl.set_arg(0, res_g)
        knl.set_arg(1, np.uint64(cube_diff))
        knl.set_arg(2, np.uint32(target_zeros))
        knl.set_arg(3, np.uint64(start_k))

        cl.enqueue_nd_range_kernel(queue, knl, (batch_size,), None)
        cl.enqueue_copy(queue, res_np, res_g)
        
        if res_np[0] > 0:
            for i in range(min(res_np[0], 10)):
                base = 1 + (i * 9)
                found_k = int(start_k) + int(res_np[base])
                
                # Big-endian display logic
                nonce_val = (found_k * cube_diff)**3 + 2040
                nbytes = max(1, (nonce_val.bit_length() + 7) // 8)
                data_hex = b"HAHA".hex() + nonce_val.to_bytes(nbytes, 'big').hex()
                hash_hex = "".join(f"{res_np[base + 1 + j]:08x}" for j in range(8))
                
                print(f"\n[MATCH] k={found_k}\nData: {data_hex}\nHash: {hash_hex}")
            
            res_np[0] = 0
            cl.enqueue_copy(queue, res_g, res_np[:1])
            
        queue.finish()

if __name__ == "__main__":
    run_opencl_miner()
