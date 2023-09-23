VERSION = "v0.5.0"
AUTHOR = "Egemen Yalin"

import os
import time
import sys

start_t = time.time()

import variables as var
from variables import colors
import functions as func
import instructions as inst

test_case = var.test_cases[-1]

TClen = len(test_case)
_disable = False
index = 0
_times_c_active = False
_times_cooldown = 0
_test_mode = False

sys.argv.pop(0)

var.settings.mode(30, False, False, False, False, True, True)

for arg in sys.argv:
	if arg == "-debug":
		var.settings.mode(30, False, False, False, True, True, True)
	elif arg == "-release":
		var.settings.mode(30, True, False, False, False, True, False)
	else:
		_test_cases_file = open(arg, "r")
		test_case = [i.strip() for i in _test_cases_file.readlines()]
		_test_cases_file.close()


def print_output(
	_case: str,
	retu: list[str] | None,
	args: tuple[int, int] | None = None,
	tab_bias: int = 0,
	comment_: str = "",
) -> None:
	if retu == []:
		var.raiseError(
			"Print Error",
			"There is a 'retu' list with no elements in 'print_output' function.",
			True,
			index,
		)
		print(f"({colors.DARK}{test_case[index]}{colors.ENDL})")
		print(colors.SECOND + "CODE HAS FORGED TO EXIT." + colors.ENDL)
		exit()
	if var.settings.skip_print or (not _times_c_active and _times_cooldown > 0):
		return
	if args == None:
		args = (index, var.addr)
	if comment_ != "":
		comment_ = f"//{comment_}"
	print(
		(colors.ERROR if args[0] > 0xFF else "")
		+ var.zero_extend(hex(args[0] % 0x100)[2:]),
		colors.DARK
		+ ("" if retu == None else var.zero_extend(hex(args[1])[2:], var.WORD))
		+ ("" if _disable else colors.ENDL)
		+ "\t",
		_case + (" " if _case else "") + colors.DARK + comment_,
		end=colors.ENDL,
	)
	if retu == None:
		print()
		return
	tmp = var.settings.tab_size - len(_case) + tab_bias - len(comment_)
	print(
		" " * tmp + colors.DARK,
		("" if retu[0] == var.STR_BIT_32 else "   ") + " ".join(retu) + colors.ENDL,
	)
	if tmp < 0:
		var.raiseError(
			"Print Breakpoint",
			f"var.settings.tab_size({var.settings.tab_size}, +{-tmp}) not big enough.",
			False,
			args[0],
		)


def proc_case(_case: str) -> list[str] | None:
	if _case == "":
		return
	global test_case, TClen, _disable, index, _times_cooldown, _times_c_active
	split = func.split_without_specs(_case)
	command = split.pop(0)

	if not split and command in var.no_input_inst:
		return var.no_input_inst[command]

	if var.settings.debug and command[0] == "#":
		command = command[1:]
		match command:
			case "jmp":
				index += var.to_sign_int(split[0])
			case "set":
				index = var.to_sign_int(split[0])
			case "flush":
				var.constants.clear()
			case _:
				var.raiseError(
					"Command",
					f"'{command}' isn't reconized by Assembler.",
					line=index,
				)
		return

	match command:
		case "org":
			var.raiseError(
				"Command",
				"'org' can only be used in first line of code.",
				line=index,
			)
		case "con":
			if split[0] in var.constants:
				var.raiseError(
					"Constant Overwrite",
					f"Isn't acceptable in this version({VERSION}).",
					line=index,
				)
				return
			var.constants[split[0]] = var.compute_int(split[1])
			check_waiters(split[0])
		case "times":
			tmp = var.compute_int(split[0])
			if tmp < 0:
				var.raiseError(
					"Index Error",
					f"The input of 'times' command cant be nagative({tmp}).",
					line=index,
				)
			if not var.settings.show_times:
				_times_c_active = True
				_times_cooldown = tmp
			TClen += tmp
			test_case = (
				test_case[: index + 1]
				+ [_case[len(split[0]) + 7 :]] * tmp
				+ test_case[index + 1 :]
			)
		case _:
			if command[0] == ":":
				command = command[1:]
				if command in var.constants:
					var.raiseError(
						"Constant Overwrite",
						f"Isn't acceptable in this version({VERSION}).",
						line=index,
					)
					return
				var.constants[command] = var.addr
				check_waiters(command)
				return proc_case(_case[len(command) + 2 :])
			if command in inst.basic_dir:
				return inst.basic_dir[command](split)
			if command in inst.command_dir:
				return inst.command_dir[command](split, command)
			if command in var.type3_inst:
				return inst.C_2input_handler(split, command)
			if command in var.shift_inst:
				return inst.C_shift(command, split)
			if command in var.jcc_inst:
				if split[0][0] == ".":
					return inst.C_Jcc(command, split[1], var.sizes[split[0][1:]])
				return inst.C_Jcc(command, split[0])
			var.raiseError(
				"Command",
				f"'{command}'({'str' if command[0].isalpha else hex(var.compute_int(command))}) isn't reconized by Assembler.",
				line=index,
			)
	return


def check_waiters(name: str) -> None:
	waiter_index = 0
	len_ = len(var.waiters)
	while waiter_index < len_:
		waiter = var.waiters[waiter_index]
		if waiter.check(name):
			if var.settings.linewrite_msg:
				var.raiseError(
					"Line Rewrite",
					f"Function found wanted values(&{', &'.join(waiter.NAMES)}, {waiter.bias}) and function rewrited as:",
					False,
					waiter.index,
				)
			waiter_end = waiter.start + (waiter.size >> 1)
			print_output(
				f"({colors.DARK}{test_case[waiter.index].split('//')[0].strip()}{colors.ENDL})",
				[var.memory[waiter.start - 1] + colors.GREEN]
				+ var.memory[waiter.start : waiter_end]
				+ [colors.DARK + var.memory[waiter_end] if waiter_end < len(var.memory) else colors.DARK],
				(waiter.index, waiter.start + var.orgin),
				9,
			)
			var.waiters.pop(waiter_index)
			len_ -= 1
		else:
			waiter_index += 1


if __name__ != "__main__":
	exit()

if _test_mode:
	print_output(
		"mov eax, *0x4321",
		["XX", "XX"],
		(0x10, 0x20),
		comment_="Bu kod testtir",
	)
	print_output("mov eax, *0x4321", ["XX", "XX"], (0x10, 0x20))
	exit()

print(f"\033[44m * \033[0m LASM Assembler {VERSION} Created by {AUTHOR}. \033[0m")

if test_case[0].startswith("org"):
	print("\t", test_case[0])
	var.addr = var.to_int(test_case[0][4:])
	var.orgin = var.addr
	test_case.pop(0)
	TClen -= 1

while index < TClen:
	case_ = test_case[index]
	if case_ == "'''":
		print(f"\t {colors.DARK}'''{colors.ENDL}")
		_disable = not _disable
		index += 1
		continue
	if var.settings.skip_times and case_.startswith("times"):
		print(
			f"\t {colors.DARK}Skip Times",
			f"{colors.ITALIC}(Line {index}){var.colors.ENDL}",
		)
		index += 1
		continue

	# *** main ***
	inst.index_ = index
	tmp_split = case_.split("//")
	case_, comment = tmp_split if len(tmp_split) == 2 else (tmp_split[0], "")
	case_ = case_.strip()
	retu = None if _disable else proc_case(case_)
	print_output(case_, retu, comment_=comment)
	if not var.settings.show_times:
		_times_c_active = False
		_times_cooldown -= 1
	if retu:
		var.addr += len(retu)
		var.memory += retu
	index += 1
	# *** end ***

	if var.event.name_list:
		var.raiseError(
			"Event Handle Error",
			f"You didint handle an Event({' '.join(var.event.name_list)}).",
			line=index,
		)

if var.waiters:
	var.raiseError("Waiter Error", "A waiter didn't get a wanted value.")
	print(" ".join(["(&" + ", &".join(waiter.names) + ")" for waiter in var.waiters]))

print("\nSize:", len(var.memory))
print(f"Time(μs): {(time.time() - start_t) * 1_000_000:,.0f}")

tmp = os.getcwd() + r"\output.txt"
print(colors.SECOND + tmp)
output_file = open(tmp, "w")
output_file.write(" ".join(var.memory))
output_file.close()

if var.waiters:
	print("Binary file skipped becouse of waiters.", var.colors.DARK)
else:
	tmp = os.getcwd() + r"\output_bin.bin"
	print(tmp, var.colors.DARK)
	output_file = open(tmp, "wb")
	output_file.write(bytes([int(i, 16) for i in var.memory]))
	output_file.close()

for const in var.constants:
	print(f"&{const}: {hex(var.constants[const])}({var.constants[const]})", end=" ")
print(colors.ENDL)
