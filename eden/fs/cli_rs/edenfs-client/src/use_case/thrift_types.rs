/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This software may be used and distributed according to the terms of the
 * GNU General Public License version 2.
 */

// Generated by
//
//
//   # Ensure thrift1 is in your path (required by the thrift compiler)
//   THRIFT=$(which thrift | xargs readlink) sudo ln -s $THRIFT /usr/local/bin/thrift1
//   # Regenerate the file and copy lib.rs into your checkout
//   buck2 run @fbcode//mode/opt fbcode//common/rust/shed/thrift_compiler:compiler --  -o /tmp/tout ~/configerator/source/scm/clients/config/usecases.thrift
//
// and manually removing logic depending on fbthrift, and `crate::types::` prefix.

#![allow(non_camel_case_types)]
pub mod scm_usecases_types {
    use serde::Deserialize;
    use serde::Serialize;

    #[derive(
        Clone,
        Debug,
        PartialEq,
        Eq,
        PartialOrd,
        Ord,
        Hash,
        Serialize,
        Deserialize
    )]
    pub struct EdenFSUseCaseLimits {
        pub max_concurrent_requests: i32,
    }

    #[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
    pub struct ScmUseCaseConfig {
        pub edenfs_limits: EdenFSUseCaseLimits,
    }

    #[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
    pub struct ScmUseCase {
        pub use_case_id: ::std::string::String,
        pub oncall: ::std::string::String,
        pub config: ScmUseCaseConfig,
    }

    #[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
    pub struct ScmUseCases {
        pub use_cases: ::std::collections::BTreeMap<::std::string::String, ScmUseCase>,
    }

    impl std::default::Default for EdenFSUseCaseLimits {
        fn default() -> Self {
            Self {
                max_concurrent_requests: 512,
            }
        }
    }
}
