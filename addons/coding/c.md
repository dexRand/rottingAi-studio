# Add-on: C / C++

## Method
- Change only what the task needs; keep the author's style and names. Complete compilable code (includes, headers, `main`); for edits show the changed block and build command.
- Don't rewrite C as C++ (or vice versa). Ambiguous request -> ask ONE short question, else state your default.

## Memory & layout
- A pointer is an address plus a type: `T *p` means `*p` has type `T`. Arrays decay to a pointer to the first element; `p[i]` is `*(p + i)`.
- Track ownership: whoever allocates frees. One `malloc`/`new` pairs with one `free`/`delete` (`delete[]` for arrays). Prefer stack objects and `std::vector`/`std::string`/`unique_ptr`.
- Check pointers before use; initialize (`T x{}`), prefer `nullptr` over `NULL`/`0`. `sizeof` is bytes, lengths use `size_t`; structs have padding, never assume a layout.

## Undefined behaviour
- Out-of-bounds access, use-after-free, double free, null/dangling dereference, signed overflow, shifts >= type width, uninitialized reads, strict aliasing.
- UB can work today and break tomorrow: treat it as a bug even when tests pass. Build with `-Wall -Wextra -Wpedantic`, C11/C++17+.

## Common bugs
- Off-by-one (`<=` on a `<` bound); `strncpy` does not terminate; `strcmp` used as a boolean (compare `== 0`); wrong `sizeof` in `malloc`/`memcpy`.
- `printf` format mismatch (`%d` vs `long`); forgotten `free`/`fclose` or leaks on early return (`goto cleanup` or RAII); unsigned underflow (`i >= 0` always true for unsigned `i`).

## Sanitizers & tools
- Build with `-g -O1 -fsanitize=address,undefined`: ASan catches out-of-bounds/use-after-free/leaks, UBSan reports UB.
- Without sanitizers: `valgrind --leak-check=full --track-origins=yes ./prog`.
- `gdb ./prog`: `run`, `bt`, `print x`, `break file:line`, `next`/`step`; `-g` is needed for symbols.
