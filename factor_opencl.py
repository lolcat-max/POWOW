import pyopencl as cl
import numpy as np
import time
import os

os.environ['PYOPENCL_CTX'] = '0'

# (Using the previous kernel_src with the __constant and max fixes)
kernel_src = r"""
#define MAX_OUT 10
typedef struct { ulong lo; ulong hi; } uint128;
uint128 mul64(ulong a, ulong b) {
    ulong a_lo = (uint)a, a_hi = a >> 32;
    ulong b_lo = (uint)b, b_hi = b >> 32;
    ulong lo = a_lo * b_lo;
    ulong mid1 = a_hi * b_lo, mid2 = a_lo * b_hi;
    ulong hi = a_hi * b_hi + (mid1 >> 32) + (mid2 >> 32);
    ulong m_lo = (mid1 & 0xFFFFFFFF) + (mid2 & 0xFFFFFFFF) + (lo >> 32);
    return (uint128){ (m_lo << 32) | (lo & 0xFFFFFFFF), hi + (m_lo >> 32) };
}
uint128 mul128(uint128 a, ulong b) {
    uint128 res = mul64(a.lo, b);
    res.hi += a.hi * b;
    return res;
}
#define ROTRIGHT(w, b) (((w) >> (b)) | ((w) << (32 - (b))))
#define CH(x, y, z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x, y, z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x) (ROTRIGHT(x, 2) ^ ROTRIGHT(x, 13) ^ ROTRIGHT(x, 22))
#define EP1(x) (ROTRIGHT(x, 6) ^ ROTRIGHT(x, 11) ^ ROTRIGHT(x, 25))
#define SIG0(x) (ROTRIGHT(x, 7) ^ ROTRIGHT(x, 18) ^ ((x) >> 3))
#define SIG1(x) (ROTRIGHT(x, 17) ^ ROTRIGHT(x, 19) ^ ((x) >> 10))
__constant uint k_sha256[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};
void sha256_transform(uint state[8], const uint data[16]) {
    uint a, b, c, d, e, f, g, h, t1, t2, m[64];
    for (int i = 0; i < 16; i++) m[i] = data[i];
    for (int i = 16; i < 64; i++) m[i] = SIG1(m[i-2]) + m[i-7] + SIG0(m[i-15]) + m[i-16];
    a=state[0]; b=state[1]; c=state[2]; d=state[3]; e=state[4]; f=state[5]; g=state[6]; h=state[7];
    for (int i = 0; i < 64; i++) {
        t1 = h + EP1(e) + CH(e,f,g) + k_sha256[i] + m[i];
        t2 = EP0(a) + MAJ(a,b,c);
        h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    state[0]+=a; state[1]+=b; state[2]+=c; state[3]+=d; state[4]+=e; state[5]+=f; state[6]+=g; state[7]+=h;
}
inline int has_nibble_zeros(const uint state[8], uint target) {
    uint bits = target * 4;
    for (uint i = 0; i < (bits/32); i++) if (state[i] != 0) return 0;
    if (bits % 32 != 0) if ((state[bits/32] >> (32 - (bits%32))) != 0) return 0;
    return 1;
}
__kernel void mine_cube_nonce(const ulong start_k, const ulong diff, const uint target, 
                              __global ulong* out_k, __global uint* count, __global uint* hashes) {
    ulong k = start_k + get_global_id(0);
    ulong root = k * diff;
    uint128 n = mul64(root, root); n = mul128(n, root);
    ulong old = n.lo; n.lo += 2040; if (n.lo < old) n.hi++;
    int nb = (n.hi == 0) ? (max((int)1, (int)((64 - clz(n.lo) + 7) / 8))) : (8 + (int)((64 - clz(n.hi) + 7) / 8));
    uint d[16] = {0};
    d[0] = 0x48414841; 
    d[1] = (uint)(n.hi >> 32); d[2] = (uint)(n.hi & 0xFFFFFFFF);
    d[3] = (uint)(n.lo >> 32); d[4] = (uint)(n.lo & 0xFFFFFFFF);
    d[15] = (4 + nb) * 8;
    uint st[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    sha256_transform(st, d);
    if (has_nibble_zeros(st, target)) {
        uint idx = atomic_inc(count);
        if (idx < MAX_OUT) {
            out_k[idx] = k;
            for (int j=0; j<8; j++) hashes[idx*8+j] = st[j];
        }
    }
}
"""

def main():
    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)
    prog = cl.Program(ctx, kernel_src).build()

    # Settings
    diff, target = 630, 13  # Reduced to 8 for realistic success
    size = 100_000_000
    start_k = np.uint64(1)
    
    mf = cl.mem_flags
    f_k, f_c, f_h = np.zeros(10, dtype=np.uint64), np.zeros(1, dtype=np.uint32), np.zeros(80, dtype=np.uint32)
    k_buf = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=f_k)
    c_buf = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=f_c)
    h_buf = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=f_h)

    print(f"Mining for {target} zeros... (Ctrl+C to stop)")
    
    while True:
        # Reset counters on GPU
        f_c[0] = 0
        cl.enqueue_copy(queue, c_buf, f_c)
        
        prog.mine_cube_nonce(queue, (size,), None, start_k, np.uint64(diff), np.uint32(target), k_buf, c_buf, h_buf)
        cl.enqueue_copy(queue, f_c, c_buf)
        
        if f_c[0] > 0:
            cl.enqueue_copy(queue, f_k, k_buf)
            cl.enqueue_copy(queue, f_h, h_buf)
            hits = min(int(f_c[0]), 10)
            for i in range(hits):
                hash_hex = "".join(f"{b:08x}" for b in f_h[i*8:(i+1)*8])
                print(f"Found! k={f_k[i]} | Hash={hash_hex}")
            break # Exit on success
            
        start_k += np.uint64(size)
        print(f"Checked up to k={start_k:,}...", end='\r')

if __name__ == "__main__": main()
