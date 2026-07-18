from cncguitarwizard.version import (
    __version__,
    PROJECT_NAME,
    PROJECT_MARK,
    MOTTO,
)

def main():
    print("=" * 60)
    print(f" {PROJECT_NAME}")
    print(f" {PROJECT_MARK}")
    print()
    print(f" {MOTTO}")
    print("=" * 60)
    print()
    print(f"Version : {__version__}")
    print("Status  : GREEN BUILD")
    print()
    print("Lift-off successful.")
    print()
    print("Rolling on the river...")

if __name__ == "__main__":
    main()
