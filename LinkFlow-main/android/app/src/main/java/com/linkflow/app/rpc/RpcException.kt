package com.linkflow.app.rpc

class RpcException(
    val code: Int,
    message: String,
    cause: Throwable? = null
) : Exception(message, cause) {

    constructor(code: String, message: String, cause: Throwable? = null)
            : this(code.toIntOrNull() ?: -32000, message, cause)

    companion object {
        const val SECURE_CHANNEL_REQUIRED = -32001
        const val TIMEOUT = -32000
        const val PAIR_FAIL = -32002
        const val NO_CONNECTION = -32003
        const val MAX_RETRIES = -32004
    }
}