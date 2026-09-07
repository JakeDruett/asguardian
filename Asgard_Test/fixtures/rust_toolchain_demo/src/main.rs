// Deliberately contains clippy lints for Asgard's Rust toolchain-orchestration tests.
fn main() {
    let numbers = vec![1, 2, 3, 4];
    if numbers.len() == 0 {
        println!("empty");
    }
    for i in 0..numbers.len() {
        println!("{}", numbers[i]);
    }
}
