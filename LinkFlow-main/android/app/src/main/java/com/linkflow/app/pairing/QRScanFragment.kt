package com.linkflow.app.pairing

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.google.zxing.BinaryBitmap
import com.google.zxing.MultiFormatReader
import com.google.zxing.PlanarYUVLuminanceSource
import com.google.zxing.common.HybridBinarizer
import com.linkflow.app.R
import java.util.concurrent.Executors

class QRScanFragment : Fragment() {
    interface Callback {
        fun onQrParsed(pairingId: String, keyB64: String)
    }

    private val reader = MultiFormatReader()
    private val executor = Executors.newSingleThreadExecutor()

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        return inflater.inflate(R.layout.fragment_qr_scan, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        val previewView = view.findViewById<PreviewView>(R.id.preview_view)
        val providerFuture = ProcessCameraProvider.getInstance(requireContext())
        providerFuture.addListener({
            val provider = providerFuture.get()
            val preview = Preview.Builder().build()
            preview.setSurfaceProvider(previewView.surfaceProvider)

            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()

            analysis.setAnalyzer(executor) { image ->
                try {
                    val plane = image.planes[0]
                    val buffer = plane.buffer
                    val data = ByteArray(buffer.remaining())
                    buffer.get(data)
                    val source = PlanarYUVLuminanceSource(
                        data,
                        image.width,
                        image.height,
                        0,
                        0,
                        image.width,
                        image.height,
                        false
                    )
                    val bitmap = BinaryBitmap(HybridBinarizer(source))
                    val result = reader.decodeWithState(bitmap).text
                    val parts = result.split(";")
                    if (parts.size == 2 && parts[0].isNotBlank() && parts[1].isNotBlank()) {
                        val cb = activity as? Callback
                        activity?.runOnUiThread {
                            cb?.onQrParsed(parts[0].trim(), parts[1].trim())
                        }
                    } else {
                        activity?.runOnUiThread {
                            Toast.makeText(requireContext(), "二维码格式错误", Toast.LENGTH_SHORT).show()
                        }
                    }
                } catch (_: Exception) {
                } finally {
                    image.close()
                }
            }

            provider.unbindAll()
            provider.bindToLifecycle(viewLifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
        }, ContextCompat.getMainExecutor(requireContext()))
    }
}

