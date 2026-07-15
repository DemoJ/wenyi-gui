import sys
import os


def _ensure_vendored_core() -> None:
    if getattr(sys, "frozen", False):
        return
    from pathlib import Path

    core_root = Path(__file__).resolve().parents[1] / "vendor" / "wenyi"
    sys.path.insert(0, str(core_root))

def patch_openai_compatible():
    try:
        import trans_novel.llm.providers.openai_compatible as oc
        orig_build = oc.build_request_kwargs
        
        def patched_build(tier_config, messages, *, json_mode=False, max_tokens=None, reasoning_style="none"):
            kwargs = orig_build(
                tier_config, messages, 
                json_mode=json_mode, 
                max_tokens=max_tokens, 
                reasoning_style=reasoning_style
            )
            # Apply max_tokens fallback for openai_compatible to prevent truncation
            if "max_tokens" not in kwargs or kwargs["max_tokens"] is None:
                try:
                    kwargs["max_tokens"] = int(os.environ.get("GUI_MAX_TOKENS", "4096"))
                except ValueError:
                    kwargs["max_tokens"] = 4096
            return kwargs
            
        oc.build_request_kwargs = patched_build

        import trans_novel.llm.providers._openai_compatible as _oc
        orig_ensure_client = _oc.OpenAICompatibleBaseClient._ensure_client
        
        def patched_ensure_client(self):
            client = orig_ensure_client(self)
            if not hasattr(client.chat.completions, "_is_patched_by_gui"):
                orig_create = client.chat.completions.create
                def patched_create(*args, **kwargs):
                    response = orig_create(*args, **kwargs)
                    try:
                        if response and getattr(response, "choices", None) and len(response.choices) > 0:
                            msg = response.choices[0].message
                            content = getattr(msg, "content", None) or ""
                            if not content.strip() and getattr(msg, "reasoning_content", None):
                                msg.content = msg.reasoning_content
                    except Exception:
                        pass
                    return response
                client.chat.completions.create = patched_create
                client.chat.completions._is_patched_by_gui = True
            return client
            
        _oc.OpenAICompatibleBaseClient._ensure_client = patched_ensure_client
    except Exception as e:
        print(f"Warning: Failed to apply GUI runtime patches: {e}", file=sys.stderr)

if __name__ == "__main__":
    # Remove the wrapper from sys.argv so typer parsing works as expected
    sys.argv[0] = "trans-novel"
    _ensure_vendored_core()
    patch_openai_compatible()
    from trans_novel.cli import main
    main()
