def foo(bar: int) -> int:
  if bar == 1:
    return 1
  return foo(bar - 1) * bar

if __name__ == "__main__":
  print(foo(10))
  assert foo(10) == 3628800
