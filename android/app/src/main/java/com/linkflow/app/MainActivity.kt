package com.linkflow.app

import android.os.Bundle
import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import com.linkflow.app.pairing.PairingActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(Intent(this, PairingActivity::class.java))
        finish()
    }
}

