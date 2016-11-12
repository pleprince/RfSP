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

import lib-sampler.glsl
import lib-pbr.glsl

// Channels declaration

// DIFFUSE
//: param custom { "default": 1.0, "label": "Diffuse Gain", "min": 0.0, "max": 1.0 }
uniform float diffuseGain;
//: param auto channel_diffuse
uniform sampler2D diffuseColor_tex;

// PRIMARY SPECULAR
//: param auto channel_user0
uniform sampler2D specularFaceColor_tex;
//: param auto channel_user1
uniform sampler2D specularEdgeColor_tex;
//: param auto channel_roughness
uniform sampler2D specularRoughness_tex;

// ROUGH SPECULAR
//: param auto channel_user2
uniform sampler2D roughSpecularFaceColor_tex;
//: param auto channel_user3
uniform sampler2D roughSpecularEdgeColor_tex;
//: param auto channel_user4
uniform sampler2D roughSpecularRoughness_tex;

// ROUGH SPECULAR
//: param auto channel_user5
uniform sampler2D clearcoatFaceColor_tex;
//: param auto channel_user6
uniform sampler2D clearcoatEdgeColor_tex;
//: param auto channel_user7
uniform sampler2D clearcoatRoughness_tex;

// IRIDESCENCE

// FUZZ

// SUBSURFACE

// SINGLE SCATTER

// GLASS

// GLOW