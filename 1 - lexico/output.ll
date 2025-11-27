; ModuleID = "bminor_module"
target triple = "arm64-apple-darwin25.0.0"
target datalayout = ""

declare i32 @"printf"(i8* %".1", ...)

@"fmt_int" = internal constant [4 x i8] c"%d\0a\00"
@"fmt_float" = internal constant [4 x i8] c"%f\0a\00"
@"fmt_true" = internal constant [6 x i8] c"true\0a\00"
@"fmt_false" = internal constant [7 x i8] c"false\0a\00"
@"fmt_str" = internal constant [4 x i8] c"%s\0a\00"
define i8 @"main"()
{
entry:
  %"x" = alloca i32
  store i32 10, i32* %"x"
  br label %"while_cond"
while_cond:
  %"x.1" = load i32, i32* %"x"
  %".4" = icmp sgt i32 %"x.1", 0
  br i1 %".4", label %"while_body", label %"while_end"
while_body:
  %"x.2" = load i32, i32* %"x"
  %".6" = getelementptr inbounds [4 x i8], [4 x i8]* @"fmt_int", i32 0, i32 0
  %".7" = call i32 (i8*, ...) @"printf"(i8* %".6", i32 %"x.2")
  %".8" = getelementptr inbounds [2 x i8], [2 x i8]* @".str.1", i32 0, i32 0
  %".9" = getelementptr inbounds [4 x i8], [4 x i8]* @"fmt_str", i32 0, i32 0
  %".10" = call i32 (i8*, ...) @"printf"(i8* %".9", i8* %".8")
  %"x.3" = load i32, i32* %"x"
  %".11" = sub i32 %"x.3", 1
  store i32 %".11", i32* %"x"
  br label %"while_cond"
while_end:
  ret i8 0
}

@".str.1" = internal constant [2 x i8] c"\0a\00"
