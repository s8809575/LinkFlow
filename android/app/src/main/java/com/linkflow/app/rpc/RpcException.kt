package com.linkflow.app.rpc

class RpcException(val code: String, override val message: String) : Exception(message)

