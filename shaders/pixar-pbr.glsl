// ----------------------------------------------------------------------------
// MIT License
//
// Copyright (c) 2016 Philippe Leprince
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
// ----------------------------------------------------------------------------

import lib-env.glsl
import lib-normal.glsl
import lib-random.glsl

//
// All channel needed are bound here.
//

//: param auto channel_emissive
uniform sampler2D emissive_tex;

//
// What kind of projection is used.
//

//: param auto is_perspective_projection
uniform bool is_perspective;

//
// Eye position in world space.
//

//: param auto world_eye_position
uniform vec3 camera_pos;

//
// Camera orientation in world space.
//

//: param auto world_camera_direction
uniform vec3 camera_dir;

//
// Number of miplevels in the envmap.
//

//: param auto environment_max_lod
uniform float maxLod;

//
// An int representing the number of samples made for specular contribution
// computation. The more the higher quality and the performance impact.
//

//: param custom {
//:   "default": 16,
//:   "label": "Quality",
//:   "widget": "combobox",
//:   "values": {
//:     "Low (4 spp)": 4,
//:     "Medium (16 spp)": 16,
//:     "High (64 spp)": 64
//:   }
//: }
uniform int nbSamples;

//
// A value used to tweak the emissive intensity.
//

//: param custom {
//:   "default": 1.0,
//:   "label": "Emissive Intensity",
//:   "min": 0.00,
//:   "max": 10.0
//: }
uniform float emissive_intensity;

//: param auto facing
uniform int facing;

bool isBackFace() {
  return facing == -1 || (facing == 0 && !gl_FrontFacing);
}

//
// BRDF related functions
//

const float EPSILON_COEF = 1e-4;

float normal_distrib(
    float ndh,
    float Roughness)
{
    // use GGX / Trowbridge-Reitz, same as Disney and Unreal 4
    // cf http://blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbs_epic_notes_v2.pdf p3
    float alpha = Roughness * Roughness;
    float tmp = alpha / max(1e-8,(ndh*ndh*(alpha*alpha-1.0)+1.0));
    return tmp * tmp * M_INV_PI;
}

vec3 fresnel(
    float vdh,
    vec3 F0)
{
    // Schlick with Spherical Gaussian approximation
    // cf http://blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbs_epic_notes_v2.pdf p3
    float sphg = pow(2.0, (-5.55473*vdh - 6.98316) * vdh);
    return F0 + (vec3(1.0, 1.0, 1.0) - F0) * sphg;
}

float G1(
    float ndw, // w is either Ln or Vn
    float k)
{
    // One generic factor of the geometry function divided by ndw
    // NB : We should have k > 0
    return 1.0 / ( ndw*(1.0-k) +  k );
}

float visibility(
    float ndl,
    float ndv,
    float Roughness)
{
    // Schlick with Smith-like choice of k
    // cf http://blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbs_epic_notes_v2.pdf p3
    // visibility is a Cook-Torrance geometry function divided by (n.l)*(n.v)
    float k = max(Roughness * Roughness * 0.5, 1e-5);
    return G1(ndl,k)*G1(ndv,k);
}

vec3 cook_torrance_contrib(
    float vdh,
    float ndh,
    float ndl,
    float ndv,
    vec3 Ks,
    float Roughness)
{
    // This is the contribution when using importance sampling with the GGX based
    // sample distribution. This means ct_contrib = ct_brdf / ggx_probability
    return fresnel(vdh,Ks) * (visibility(ndl,ndv,Roughness) * vdh * ndl / ndh );
}

vec3 importanceSampleGGX(vec2 Xi, vec3 A, vec3 B, vec3 C, float roughness)
{
    float a = roughness*roughness;
    float cosT = sqrt((1.0-Xi.y)/(1.0+(a*a-1.0)*Xi.y));
    float sinT = sqrt(1.0-cosT*cosT);
    float phi = 2.0*M_PI*Xi.x;
    return (sinT*cos(phi)) * A + (sinT*sin(phi)) * B + cosT * C;
}

float probabilityGGX(float ndh, float vdh, float Roughness)
{
    return normal_distrib(ndh, Roughness) * ndh / (4.0*vdh);
}

float distortion(vec3 Wn)
{
    // Computes the inverse of the solid angle of the (differential) pixel in
    // the cube map pointed at by Wn
    float sinT = sqrt(1.0-Wn.y*Wn.y);
    return sinT;
}

float computeLOD(vec3 Ln, float p)
{
    return max(0.0,
               (maxLod-1.5) - 0.5*(log(float(nbSamples)) + log( p * distortion(Ln) ))
               * M_INV_LOG2);
}

//
// Compute the outgoing light radiance to the viewer's eye
//

vec4 pbrComputeBRDF(V2F inputs, vec3 diffColor, vec3 specColor,
                    float glossiness, float occlusion)
{

    // Get world space normal
    //
    vec3 normal_vec = computeWSNormal(inputs.tex_coord, inputs.tangent,
                                      inputs.bitangent, inputs.normal);

    // Double-sided normal if back faces are visible
    //
    if (isBackFace())
    {
        normal_vec = -normal_vec;
    }

    vec3 eye_vec = is_perspective ?
                   normalize(camera_pos - inputs.position) :
                   -camera_dir;
    float ndv = dot(eye_vec, normal_vec);

    // Trick to remove black artefacts Backface ? place the eye at the
    // opposite - removes black zones
    //
    if (ndv < 0) {
        eye_vec = reflect(eye_vec, normal_vec);
        ndv = abs(ndv);
    }

    // Create a local basis for BRDF work
    //
    // local tangent
    vec3 Tp = normalize(inputs.tangent
                        - normal_vec*dot(inputs.tangent, normal_vec));
    // local bitangent
    vec3 Bp = normalize(inputs.bitangent
                        - normal_vec*dot(inputs.bitangent, normal_vec)
                        - Tp*dot(inputs.bitangent, Tp));

    // Diffuse contribution
    //
    vec3 contribE = occlusion * envIrradiance(normal_vec) * diffColor;

    // Specular contribution
    //
    float roughness = 1.0 - glossiness;
    vec3 contribS = vec3(0.0);
    for(int i=0; i<nbSamples; ++i)
    {
        vec2 Xi = hammersley2D(i, nbSamples);
        vec3 Hn = importanceSampleGGX(Xi,Tp,Bp,normal_vec,roughness);
        vec3 Ln = -reflect(eye_vec,Hn);
        float ndl = dot(normal_vec, Ln);

        // Horizon fading trick from
        // http://marmosetco.tumblr.com/post/81245981087
        const float horizonFade = 1.3;
        float horiz = clamp( 1.0 + horizonFade * ndl, 0.0, 1.0 );
        horiz *= horiz;

        ndl = max( 1e-8, abs(ndl) );
        float vdh = max(1e-8, dot(eye_vec, Hn));
        float ndh = max(1e-8, dot(normal_vec, Hn));
        float lodS = roughness < 0.01 ? 0.0 : computeLOD(Ln,
        probabilityGGX(ndh, vdh, roughness));
        contribS += envSampleLOD(Ln, lodS) *
                    cook_torrance_contrib(vdh, ndh, ndl, ndv, specColor, roughness) * horiz;
    }

    // Remove occlusions on shiny reflections
    //
    contribS *= mix(occlusion, 1.0, glossiness * glossiness) / float(nbSamples);

    // Emissive
    //
    vec3 contribEm = emissive_intensity *
                     texture2D(emissive_tex, inputs.tex_coord).rgb;

    // Sum diffuse + spec + emissive
    //
    return vec4(contribS + contribE + contribEm, 1.0);
}