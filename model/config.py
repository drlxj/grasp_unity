
model_config = dict(

  bps_params=dict(
      filepath="./data",
      dtype="torch.float32",
  ),

  encoder_subject_params=dict(
      in_dim=60,  # subject input dimension
      out_dim=256,
      n_mlp_block=4,
  ),

  encoder_subjectobject_params=dict(
      in_dim=1280,  # subject-object combined input dimension
      out_dim=256,
      n_mlp_block=4,
  ),

)
