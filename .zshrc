export PATH="/usr/local/opt/python@3.11/bin:$PATH"



# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/J.S.Park/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/J.S.Park/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/J.S.Park/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/J.S.Park/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

export TESSDATA_PREFIX=$(brew --prefix)/share/tessdata


