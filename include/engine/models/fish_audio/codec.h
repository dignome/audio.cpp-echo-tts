#pragma once

#include "engine/framework/assets/tensor_source.h"
#include "engine/framework/core/backend.h"
#include "engine/models/fish_audio/assets.h"
#include "engine/models/fish_audio/types.h"

#include <cstdint>
#include <memory>
#include <vector>

namespace engine::models::fish_audio {

class FishAudioCodecRuntime {
public:
    FishAudioCodecRuntime(
        std::shared_ptr<const FishAudioAssets> assets,
        core::BackendConfig backend,
        int threads,
        size_t graph_arena_bytes,
        size_t weight_context_bytes,
        assets::TensorStorageType matmul_weight_storage_type,
        assets::TensorStorageType conv_weight_storage_type);
    ~FishAudioCodecRuntime();

    FishAudioCodes encode_reference(const runtime::AudioBuffer & audio);
    runtime::AudioBuffer decode(const FishAudioCodes & codes);

    // Continuous-latent access to the same autoencoder. Echo-TTS conditions on
    // and generates z_q directly and never materialises codebook indices.
    // `values` is (frames, channels) row-major.
    FishAudioLatents encode_zq(const runtime::AudioBuffer & audio);
    runtime::AudioBuffer decode_zq(const std::vector<float> & latents, int64_t frames);
    void release_encode_graph();
    void release_runtime_graphs();

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace engine::models::fish_audio
