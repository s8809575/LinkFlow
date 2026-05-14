package com.linkflow.app.pairing

import android.text.Editable
import android.text.TextWatcher

class SimpleWatcher(private val after: () -> Unit) : TextWatcher {
    override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, afterCount: Int) {}
    override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
    override fun afterTextChanged(s: Editable?) {
        after()
    }
}

