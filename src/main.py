from model import AnthropicModel

def main():
    model = AnthropicModel()
    model.handle_message("Hi, can you tell me if this message sent? Please think about it in circles with the thinking budget you're allowed")

if __name__ == "__main__":
    main()